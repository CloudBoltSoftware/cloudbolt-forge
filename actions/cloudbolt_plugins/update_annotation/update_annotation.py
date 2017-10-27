import time
import pyVmomi
import datetime
from common.methods import set_progress
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper


def get_vmware_service_instance(vcenter_rh):
    """
    :return: the pyvmomi service instance object that represents a connection to vCenter,
    and which can be used for making API calls.
    """
    assert isinstance(vcenter_rh, VsphereResourceHandler)
    vcenter_rh.init()
    wc = vcenter_rh.resource_technology.work_class
    assert isinstance(wc, TechnologyWrapper)
    return wc._get_connection()


def run(job, logger=None, **kwargs):
    server = job.server_set.first()
    rh = server.resource_handler.cast()
    owner = job.owner

    # Connect to RH
    si = get_vmware_service_instance(rh)
    vm = get_vm_by_uuid(si, server.resource_handler_svr_id)
    assert isinstance(vm, pyVmomi.vim.VirtualMachine)

    # Set the new VM annotation
    set_progress("Updating new virtual machine annotation")
    cur_date = datetime.datetime.now()
    annotation = str('{{ append_annotation }}')
    annotation = server.notes + annotation
    assert isinstance(vm, pyVmomi.vim.VirtualMachine)
    configSpec = pyVmomi.vim.vm.ConfigSpec()
    configSpec.annotation = annotation
    vm.ReconfigVM_Task(configSpec)

    set_progress("Updating server info from VMware")
    time.sleep(15)
    server.refresh_info()

    return "", "", ""


if __name__ == '__main__':
    import os
    import sys

    localpath = os.path.join('var', 'opt', 'cloudbolt')
    sys.path.append(localpath)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    job_id = sys.argv[1]
    print run(job=job_id)