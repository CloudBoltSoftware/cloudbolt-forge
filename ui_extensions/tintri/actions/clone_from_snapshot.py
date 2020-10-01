from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def should_display(*args, **kwargs):
    """
    This action is exposed in the Tintri extension tab
    Should never be added to the left panel on any server
    """
    return False

def run(job, server, **kwargs):
    set_progress("we are here: clone_from_snapshot")
    set_progress(f"server: {server}")
    set_progress(f"kwargs: {kwargs}")
    set_progress("New name: {{ new_vm_name }}")
