from common.methods import set_progress
from utilities.logger import ThreadLogger
from xui.azure_patches.views import scan_vm_for_patches, apply_all_vm_patches

logger = ThreadLogger(__name__)

def run(job, server, **kwargs):
    logger.debug("Starting Azure Patch operation")
    operation = kwargs['operation']
    if not operation:
        return "FAILURE", "No operation specified", ""
    set_progress(f"Starting patch scan operation for server: {server.hostname}")
    if operation == "scan_vm_for_patches":
        scan_vm_for_patches(server)
        msg = "Azure Scan operation completed successfully."

    if operation == "apply_all_vm_patches":
        apply_all_vm_patches(server)
        msg = "Azure Patch operation completed successfully."

    set_progress(msg)
    return "SUCCESS", msg, ""
