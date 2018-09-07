import time
import pyVmomi

from pyVmomi import vim
from common.methods import set_progress
from resourcehandlers.vmware.pyvmomi_wrapper import get_vm_by_uuid, wait_for_tasks
from resourcehandlers.vmware.models import VsphereResourceHandler
from resourcehandlers.vmware.vmware_41 import TechnologyWrapper
from utilities.logger import ThreadLogger


DESIRED_VMX_VERSION = "11"
ALWAYS_UPGRADE_TOOLS = True
ALLOW_FORCED_POWERDOWN = True


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

    if not logger:
        logger = ThreadLogger(__name__)

    si = None
    failure_msg = ""

    for server in job.server_set.all():

        rh = server.resource_handler
        if not si:
            si = get_vmware_service_instance(rh)
        vm = get_vm_by_uuid(si, server.resource_handler_svr_id)

        assert isinstance(vm, pyVmomi.vim.VirtualMachine)

        server.refresh_info()

        server_original_power_status = server.power_status

        # Getting the snapshot. Remember kids, safety first.
        set_progress("Creating snapshot on {}".format(server.hostname))
        current_hw_version = str(vm.config.version)

        try:
            rh.cast().create_snapshot(server, "version{}-{}".format(current_hw_version, time.time()),
                                      "Pre Hardware / Tools Upgrade Snapshot ({})".format(current_hw_version))

        # TODO: Figure out what all can be thrown at us by create_snapshot()
        except Exception as err:
            failure_msg = "Could not create a snapshot for VM {}".format(server.hostname)
            set_progress("{}, the error was: {}, aborting upgrade".format(failure_msg, err))
            continue

        # Usually tools needs an upgrade before we convert the VMX version, so doing that first
        if server_original_power_status != "POWERON":
            set_progress("Server {} is off. Turning it on to upgrade VMware Tools.".format(server.hostname))

            try:
                server.power_on()
            except Exception as err:
                if ALWAYS_UPGRADE_TOOLS:
                    set_progress("Could not turn on server to upgrade VMware Tools. Skipping server {}".format(server.hostname))
                    continue
                pass
            server.refresh_info()

        set_progress("Upgrading VMware Tools on {}".format(server.hostname))

        # Upgrade VMware tools
        try:
            task = vm.UpgradeTools_Task()
            wait_for_tasks(si, [task])
        except (vim.fault.InvalidState, vim.fault.NotSupported, vim.fault.RuntimeFault, vim.fault.TaskInProgress,
                vim.fault.ToolsUnavailable, vim.fault.VmConfigFault, vim.fault.VmToolsUpgradeFault) as err:
            if ALWAYS_UPGRADE_TOOLS:
                failure_msg = "Could not upgrade VMware Tools on {} ({}).".format(server.hostname, err)
                set_progress("{} Skipping server.".format(failure_msg))
                continue
            set_progress(
                "Cannot upgrade VM tools because of {}. Will still try to upgrade hardware version on {}.".format(err, server.hostname))
            pass

        # Updating VM hw version
        desired_version = "vmx-{}".format(DESIRED_VMX_VERSION)
        if vm.config.version == desired_version:
            set_progress("Hardware version already updated on server {}. Nothing to do.".format(server.hostname))
            continue

        if server.power_status != "POWEROFF":
            set_progress("Powering off server {} to upgrade HW version".format(server.hostname))
            try:
                server.power_off()
            except Exception as err:
                if ALLOW_FORCED_POWERDOWN:
                    set_progress("Server {} did not power down in time. Forcing.".format(server.hostname))
                    try:
                        task = vm.PowerOffVM_Task()
                        wait_for_tasks(si, [task])
                    except () as err:
                        failure_msg = "Server {} reported error {} when forcing power down.".format(server.hostname, err)
                        set_progress("{} Skipping VM hardware upgrade".format(failure_msg))
                        continue
                else:
                    failure_msg = "Server {} did not power down and we're not forcing it to.".format(server.hostname)
                    set_progress("{} Skipping VM hardware upgrade".format(failure_msg))
                    continue

            server.refresh_info()

        try:
            set_progress("Updating HW version to {} on {}".format(DESIRED_VMX_VERSION, server.hostname))
            task = vm.UpgradeVM_Task(version=desired_version)
            wait_for_tasks(si, [task])
        except vim.fault.AlreadyUpgraded:
            set_progress("VM was already at the desired version")
            pass
        except (vim.fault.InvalidPowerState, vim.fault.InvalidState, vim.fault.NoDiskFound, vim.fault.RuntimeFault,
                vim.fault.TaskInProgress) as err:
            failure_msg = "Failed to upgrade hardware version because of {}".format(err)
            set_progress("{}. Will now return VM to original power state.".format(failure_msg))
            pass

        if server_original_power_status == "POWERON":
            set_progress("Server was originally on, so power it on again")
            server.power_on()

            if failure_msg:
                return "FAILURE", "", "Last error reported: {}. Please check the job logs.".format(failure_msg)

    if failure_msg:
        return "FAILURE", "", "Last error reported: {}. Please check the job logs".format(failure_msg)

    return "", "", ""
