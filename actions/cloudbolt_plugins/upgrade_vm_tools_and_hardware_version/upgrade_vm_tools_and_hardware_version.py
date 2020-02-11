import time
import pyVmomi

from common.methods import set_progress
from infrastructure.models import Server, Environment, CustomField
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid, wait_for_tasks, get_connection
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper


# Make sure the cf we use exists
cf, is_new = CustomField.objects.get_or_create(
    name='vmx_versions', type='TXT',
    defaults={'label': 'Valid VM Hardware versions',
              'description': 'List of valid VM Hardware versions to choose from'
              }
)


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

    return get_connection(rh.ip, rh.port, rh.serviceaccount, rh.servicepasswd, ssl_verification=False)


def run(job, logger=None, server=None, **kwargs):

    si = None
    for server in job.server_set.all():
        if not si:
            si = get_vmware_service_instance(server.resource_handler.cast())
        vm = get_vm_by_uuid(si, server.resource_handler_svr_id)

        assert isinstance(vm, pyVmomi.vim.VirtualMachine)

        parameters = job.job_parameters.cast()
        user_target_version = parameters.target_version or None
        target_version = determine_target_version(server, user_target_version)

        if vm.config.version == target_version:
            set_progress("Hardware version already up-to-date. Nothing to do.")
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
        if target_version:
            target_version_text = target_version
        else:
            target_version_text = "latest"
        task = vm.CreateSnapshot_Task(name="hwupg-{}-to-{}-{}".format(vm.config.version,
                                                                      target_version_text,
                                                                      time.time()),
                                      description="Pre Hardware Upgrade Snapshot", memory=False, quiesce=True)
        wait_for_tasks(si, [task])

        failure_msg = ""

        # Upgrade VM
        try:
            set_progress("Updating HW version")
            if target_version:
                task = vm.UpgradeVM_Task(version=target_version)
            else:
                task = vm.UpgradeVM_Task()
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


def determine_target_version(server, user_target_version):

    if user_target_version:
        if user_target_version in server.environment.vmx_versions:
            return user_target_version
        else:
            raise AttributeError
    # User did not specify, we will not either and default to VMware's latest
    return None


if __name__ == '__main__':
    # if len(sys.argv) != 2:
    #     print '  Usage:  {} <server_id>'.format(sys.argv[0])
    #     sys.exit(1)

    # s = Server.objects.get(id=sys.argv[1])
    s = Server.objects.get(id=65)
    print(run(None, None, s))
