import sys
import time
import pyVmomi

from common.methods import set_progress
from infrastructure.models import Server
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid, wait_for_tasks
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper

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


def run(job, logger=None, server=None, **kwargs):

    si = None
    for server in job.server_set.all():
        if not si:
            si = get_vmware_service_instance(server.resource_handler.cast())
        vm = get_vm_by_uuid(si, server.resource_handler_svr_id)
    
        assert isinstance(vm, pyVmomi.vim.VirtualMachine)
        
        server.refresh_info()

        server_original_power_status = server.power_status
        set_progress("Performing VM hard reset...")
        task = vm.ResetVM_Task()
        wait_for_tasks(si, [task])

    return "", "", ""