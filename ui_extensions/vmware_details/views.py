import pyVmomi
from django.shortcuts import render
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper

# UI Extension that exposes basic VM / VM Tools information to an end-user in a server-tab
#
# Copyright 2018 Aves-IT B.V.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


class VMWareDetailsTabDelegate(TabExtensionDelegate):
    def should_display(self):
        return isinstance(self.instance.resource_handler.cast(), VsphereResourceHandler)


def get_vmware_service_instance(rh):
    """
    Gets a service instance object that represents a connection to vCenter,
    and which can be used for making API calls.

    :param rh: ResourceHandler to get a ServiceInstance for
    :type rh: ResourceHandler
    :return: ServiceInstance object
    """

    assert isinstance(rh.cast(), VsphereResourceHandler)
    rh_api = rh.get_api_wrapper()

    assert isinstance(rh_api, TechnologyWrapper)

    return rh_api._get_connection()


@tab_extension(model=Server, title='VMWare Details', delegate=VMWareDetailsTabDelegate)
def vmware_details_server_tab(request, obj_id):
    """
    Renders the VMWare Info tab in the Server view

    :param request: the HTTP request
    :param obj_id: the server ID
    :return: a rendered object
    """
    server = Server.objects.get(id=obj_id)

    si = get_vmware_service_instance(server.resource_handler)
    vm = get_vm_by_uuid(si, server.resource_handler_svr_id)

    assert isinstance(vm, pyVmomi.vim.VirtualMachine)

    # You can pass basically anything from the pyvmomi vm object here into the template
    # Either as raw api result (vm.config.version) or after a modification/lookup (vm.guest.toolsRunningStatus)

    conv = {
        'guestToolsRunning': 'VMware Tools is running.',
        'guestToolsNotRunning': 'VMware Tools is not running.',
        'guestToolsExecutingScripts': 'VMware Tools is starting.',
        'guestToolsBlacklisted': 'VMware Tools is installed, but should be upgraded immediately due to a known bug',
        'guestToolsUnmanaged': 'VMware Tools is installed, but it is not managed by VMWare. Probably open-vm-tools',
        'guestToolsNeedUpgrade': 'VMware Tools is installed, but the version is not current.',
        'guestToolsSupportedOld': 'VMware Tools is installed, supported, but a newer version is available.',
        'guestToolsTooOld': 'VMware Tools is installed, but the version is too old.',
        'guestToolsTooNew': 'VMware Tools is installed, but the version is too new for this virtual machine.',
        'guestToolsNotInstalled': 'VMware Tools has never been installed.',
        'guestToolsSupportedNew': 'VMware Tools is installed, supported, and newer than the version on the host.',
        'guestToolsCurrent': 'VMware Tools is installed, and the version is current.'
    }

    vm_details = {
        'vmx_version': vm.config.version,
        'vmtools_status': conv.get(vm.guest.toolsRunningStatus, 'Unknown ({})'.format(vm.guest.toolsRunningStatus)),
        'vmtools_version': conv.get(vm.guest.toolsVersionStatus2, 'Unknown ({})'.format(vm.guest.toolsVersionStatus2))
    }

    return render(request, 'vmware_details/templates/vmware_tab.html', dict(server=server, vm_details=vm_details))
