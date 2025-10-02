from common.methods import set_progress
from utilities.logger import ThreadLogger
from xui.ssm_inventory.views import patch_ec2_instance

logger = ThreadLogger(__name__)

def run(job, server, **kwargs):
    logger.debug("Starting patch_ec2_instance operation")
    operation = kwargs.get("operation")
    reboot_option = kwargs.get("reboot_option")

    set_progress(f"Starting patch operation '{operation}' with reboot option "
                 f"'{reboot_option}' for server: {server.hostname}.")
    patch_ec2_instance(server, operation=operation, reboot_option=reboot_option)

    set_progress("patch_ec2_instance operation completed")
    return "SUCCESS", "Patch operation completed successfully.", ""

