# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Modules required to work with ironic_inspector:
    https://pypi.python.org/pypi/ironic-discoverd
"""

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from ironic.common import exception
from ironic.common.i18n import _
from ironic.common.i18n import _LE
from ironic.common.i18n import _LI
from ironic.common import keystone
from ironic.common import states
from ironic.conductor import task_manager
from ironic.drivers import base


LOG = logging.getLogger(__name__)


inspector_opts = [
    cfg.BoolOpt('enabled', default=False,
                help='whether to enable inspection using ironic-inspector',
                deprecated_group='discoverd'),
    cfg.StrOpt('service_url',
               help='ironic-inspector HTTP endpoint. If this is not set, the '
               'ironic-inspector client default (http://127.0.0.1:5050) '
               'will be used.',
               deprecated_group='discoverd'),
    cfg.IntOpt('status_check_period', default=60,
               help='period (in seconds) to check status of nodes '
               'on inspection',
               deprecated_group='discoverd'),
]

CONF = cfg.CONF
CONF.register_opts(inspector_opts, group='inspector')


# TODO(dtantsur): change this to ironic_inspector_client once it's available
ironic_inspector = importutils.try_import('ironic_inspector')
if not ironic_inspector:
    # NOTE(dtantsur): old name for ironic-inspector
    ironic_inspector = importutils.try_import('ironic_discoverd')
if ironic_inspector:
    from ironic_inspector import client


class Inspector(base.InspectInterface):
    """In-band inspection via ironic-inspector project."""

    @classmethod
    def create_if_enabled(cls, driver_name):
        """Create instance of Inspector if it's enabled.

        Reports log warning with given driver_name if it's not.

        :return: Inspector instance or None
        """
        if CONF.inspector.enabled:
            return cls()
        else:
            LOG.info(_LI("Inspection via ironic-inspector is disabled in "
                         "configuration for driver %s. To enable, change "
                         "[inspector] enabled = True."), driver_name)

    def __init__(self):
        if not CONF.inspector.enabled:
            raise exception.DriverLoadError(
                _('ironic-inspector support is disabled'))

        if not ironic_inspector:
            raise exception.DriverLoadError(
                _('ironic-inspector Python module not found'))

        # NOTE(dtantsur): __version_info__ attribute appeared in 1.0.0
        version = getattr(ironic_inspector, '__version_info__', (0, 2))
        if version < (1, 0):
            raise exception.DriverLoadError(
                _('ironic-inspector version is too old: required >= 1.0.0, '
                  'got %s') % '.'.join(str(x) for x in version))

    def get_properties(self):
        """Return the properties of the interface.

        :returns: dictionary of <property name>:<property description> entries.
        """
        return {}  # no properties

    def validate(self, task):
        """Validate the driver-specific inspection information.

        If invalid, raises an exception; otherwise returns None.

        :param task: a task from TaskManager.
        """
        # NOTE(deva): this is not callable if inspector is disabled
        #             so don't raise an exception -- just pass.
        pass

    def inspect_hardware(self, task):
        """Inspect hardware to obtain the hardware properties.

        This particular implementation only starts inspection using
        ironic-inspector. Results will be checked in a periodic task.

        :param task: a task from TaskManager.
        :returns: states.INSPECTING
        """
        LOG.debug('Starting inspection for node %(uuid)s using '
                  'ironic-inspector client %(version)s',
                  {'uuid': task.node.uuid, 'version':
                   ironic_inspector.__version__})

        # NOTE(dtantsur): we're spawning a short-living green thread so that
        # we can release a lock as soon as possible and allow ironic-inspector
        # to operate on a node.
        eventlet.spawn_n(_start_inspection, task.node.uuid, task.context)
        return states.INSPECTING

    @base.driver_periodic_task(spacing=CONF.inspector.status_check_period,
                               enabled=CONF.inspector.enabled)
    def _periodic_check_result(self, manager, context):
        """Periodic task checking results of inspection."""
        filters = {'provision_state': states.INSPECTING}
        node_iter = manager.iter_nodes(filters=filters)

        for node_uuid, driver in node_iter:
            try:
                # TODO(dtantsur): we need an exclusive lock only once
                # inspection is finished.
                with task_manager.acquire(context, node_uuid) as task:
                    _check_status(task)
            except (exception.NodeLocked, exception.NodeNotFound):
                continue


def _call_inspector(func, uuid, context):
    """Wrapper around calls to inspector."""
    # NOTE(dtantsur): due to bug #1428652 None is not accepted for base_url.
    kwargs = {}
    if CONF.inspector.service_url:
        kwargs['base_url'] = CONF.inspector.service_url
    return func(uuid, auth_token=context.auth_token, **kwargs)


def _start_inspection(node_uuid, context):
    """Call to inspector to start inspection."""
    try:
        _call_inspector(client.introspect, node_uuid, context)
    except Exception as exc:
        LOG.exception(_LE('Exception during contacting ironic-inspector '
                          'for inspection of node %(node)s: %(err)s'),
                      {'node': node_uuid, 'err': exc})
        # NOTE(dtantsur): if acquire fails our last option is to rely on
        # timeout
        with task_manager.acquire(context, node_uuid) as task:
            task.node.last_error = _('Failed to start inspection: %s') % exc
            task.process_event('fail')
    else:
        LOG.info(_LI('Node %s was sent to inspection to ironic-inspector'),
                 node_uuid)


def _check_status(task):
    """Check inspection status for node given by a task."""
    node = task.node
    if node.provision_state != states.INSPECTING:
        return
    if not isinstance(task.driver.inspect, Inspector):
        return

    LOG.debug('Calling to inspector to check status of node %s',
              task.node.uuid)

    # NOTE(dtantsur): periodic tasks do not have proper tokens in context
    task.context.auth_token = keystone.get_admin_auth_token()
    try:
        status = _call_inspector(client.get_status, node.uuid, task.context)
    except Exception:
        # NOTE(dtantsur): get_status should not normally raise
        # let's assume it's a transient failure and retry later
        LOG.exception(_LE('Unexpected exception while getting '
                          'inspection status for node %s, will retry later'),
                      node.uuid)
        return

    if status.get('error'):
        LOG.error(_LE('Inspection failed for node %(uuid)s '
                      'with error: %(err)s'),
                  {'uuid': node.uuid, 'err': status['error']})
        node.last_error = (_('ironic-inspector inspection failed: %s')
                           % status['error'])
        task.process_event('fail')
    elif status.get('finished'):
        LOG.info(_LI('Inspection finished successfully for node %s'),
                 node.uuid)
        task.process_event('done')
