# Copyright 2015 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""This module provides mock 'specs' for third party modules that can be used
when needing to mock those third party modules"""

# iboot
IBOOT_SPEC = (
    'iBootInterface',
)

# ironic_inspector
IRONIC_INSPECTOR_SPEC = (
    '__version__',
    '__version_info__',
    'client',
)

# proliantutils
PROLIANTUTILS_SPEC = (
    'exception',
    'ilo',
)

# pyghmi
PYGHMI_SPEC = (
    'exceptions',
    'ipmi',
)
PYGHMI_EXC_SPEC = (
    'IpmiException',
)
PYGHMI_IPMI_SPEC = (
    'command',
)
PYGHMI_IPMICMD_SPEC = (
    'boot_devices',
    'Command',
)

# pyremotevbox
PYREMOTEVBOX_SPEC = (
    'exception',
    'vbox',
)
PYREMOTEVBOX_EXC_SPEC = (
    'PyRemoteVBoxException',
    'VmInWrongPowerState',
)
PYREMOTEVBOX_VBOX_SPEC = (
    'VirtualBoxHost',
)

# pywsman
PYWSMAN_SPEC = (
    'Client',
    'ClientOptions',
    'EndPointReference',
    'FLAG_ENUMERATION_OPTIMIZATION',
    'Filter',
    'XmlDoc',
    'wsman_transport_set_verify_host',
    'wsman_transport_set_verify_peer',
)

# pywsnmp
PYWSNMP_SPEC = (
    'entity',
    'error',
    'proto',
)

# scciclient
SCCICLIENT_SPEC = (
    'irmc',
)
SCCICLIENT_IRMC_SCCI_SPEC = (
    'POWER_OFF',
    'POWER_ON',
    'POWER_RESET',
    'SCCIClientError',
    'get_client',
    'get_report',
    'get_sensor_data',
)

# seamicro
SEAMICRO_SPEC = (
    'client',
    'exceptions',
)
# seamicro.client module
SEAMICRO_CLIENT_MOD_SPEC = (
    'Client',
)
SEAMICRO_EXC_SPEC = (
    'ClientException',
    'UnsupportedVersion',
)
