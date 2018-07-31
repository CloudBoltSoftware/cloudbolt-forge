import pyVmomi
import datetime
from common.methods import set_progress
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid, wait_for_tasks
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper
from jobengine.jobmodules.syncvmsjob import SyncVMsClass


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

def check_task(si, task):
    wait_for_tasks(si, [task], timeout=3600)
    task_info = task.info
    uuid = task_info.result.config.uuid
    return uuid


def run(job, logger=None, **kwargs):
    server = job.server_set.first()
    rh = server.resource_handler.cast()
    group = server.group
    env = server.environment
    owner = job.owner
    new_name = str('{{ clone_name }}')
    do_linked_clone = True if '{{ linked_clone }}' == 'True' else False

    # Connect to RH
    si = get_vmware_service_instance(rh)
    vm = get_vm_by_uuid(si, server.resource_handler_svr_id)
    assert isinstance(vm, pyVmomi.vim.VirtualMachine)

    # Define the location, empty defaults to same location as the source vm
    set_progress("Generating VMware Clone Config")
    relocate_spec = pyVmomi.vim.vm.RelocateSpec()

    # Linked clone
    if do_linked_clone:
        set_progress('Clones as "Linked Clone"')
        relocate_spec.diskMoveType = 'createNewChildDiskBacking'

    # Define the clone config specs
    cloneSpec = pyVmomi.vim.vm.CloneSpec(
        powerOn=False,
        template=False,
        snapshot=None,
        location=relocate_spec)

    # Clone the Virtual Machine with provided specs
    set_progress("Cloning {} to {}".format(server.hostname, new_name))
    clone_task = vm.Clone(name=new_name, folder=vm.parent, spec=cloneSpec)

    # Wait for completion and get the new vm uuid
    uuid = check_task(si, clone_task)

    # Set the new VM annotation
    set_progress("Updating new virtual machine annotation")
    clone_add_date = datetime.datetime.now()
    annotation = 'Cloned by {} using CloudBolt on {} [Job ID={}]'.format(
        owner, clone_add_date, job.id)
    new_vm = get_vm_by_uuid(si, uuid)
    assert isinstance(new_vm, pyVmomi.vim.VirtualMachine)
    configSpec = pyVmomi.vim.vm.ConfigSpec()
    configSpec.annotation = annotation
    new_vm.ReconfigVM_Task(configSpec)

    # Sync the cloned VM to CloudBolt
    # TODO: change this to just Server.objects.create() so that we can have the first history
    # event for the server say it was created by this job, rather than discovered by sync VMs
    vm = {}
    vm['hostname'] = new_name
    vm['uuid'] = uuid
    vm['power_status'] = 'POWEROFF'
    sync_class = SyncVMsClass()
    (newserver, status, errors) = sync_class.import_vm(vm, rh, group, env, owner)
    if newserver:
        set_progress("Adding server to job")
        job.server_set.add(newserver)
        set_progress("Updating server info from VMware")
        newserver.refresh_info()

    if errors:
        return ("WARNING",
                "The clone task completed, but the new server could not be detected",
                errors)

    return "", "", ""


if __name__ == '__main__':
    import os
    import sys

    localpath = os.path.join('var', 'opt', 'cloudbolt')
    sys.path.append(localpath)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    job_id = sys.argv[1]
    print(run(job=job_id))
