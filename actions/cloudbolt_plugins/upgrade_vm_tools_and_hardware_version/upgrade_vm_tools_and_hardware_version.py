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

        if vm.config.version == "vmx-08":
            set_progress("Hardware version already updated. Nothing to do.")
            continue

        server.refresh_info()

        server_original_power_status = server.power_status
        if server_original_power_status != "POWERON":
            set_progress("Server is off. Turning it on to upgrade VMware Tools.")
            # Make sure VM is powered on
            task = vm.PowerOnVM_Task()
            wait_for_tasks(si, [task])

        set_progress("Upgrading VMware Tools")
        # Upgrade VMware tools
        try:
            task = vm.UpgradeTools_Task()
            wait_for_tasks(si, [task])
        except:
            set_progress("Cannot upgrade VM tools. Will still try to upgrade hardware version. ")
            pass

        # Power off VM for hw upgrade
        set_progress("Powering off server to upgrade HW version")
        task = vm.PowerOffVM_Task()
        wait_for_tasks(si, [task])

        # Snapshot VM
        set_progress("Creating snapshot")
        # server.resource_handler.cast().create_snapshot(server, "version4hw-{}".format(time.time()), "Pre Hardware Upgrade Snapshot")

        task = vm.CreateSnapshot_Task("version4hw-{}".format(time.time()), "Pre Hardware Upgrade Snapshot", False, True)
        wait_for_tasks(si, [task])

        failure_msg = ""

        # Upgrade VM
        try:
            set_progress("Updating HW version")
            task = vm.UpgradeVM_Task(version="vmx-08")
            wait_for_tasks(si, [task])
        except:
            failure_msg = "Failed to upgrade hardware version"
            set_progress("{}. Will now return VM to original power state.".format(failure_msg))
            pass

        if server_original_power_status == "POWERON":
            set_progress("Server was originally on, so power it on again")
            task = vm.PowerOnVM_Task()
            wait_for_tasks(si, [task])

        if failure_msg:
            return "FAILURE", "", failure_msg

        return "", "", ""

    return "", "", ""


if __name__ == '__main__':
    # if len(sys.argv) != 2:
    #     print '  Usage:  {} <server_id>'.format(sys.argv[0])
    #     sys.exit(1)

    # s = Server.objects.get(id=sys.argv[1])
    s = Server.objects.get(id=65)
    print(run(None, None, s))
