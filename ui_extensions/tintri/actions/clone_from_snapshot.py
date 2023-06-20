from common.methods import set_progress
from utilities.logger import ThreadLogger
from xui.tintri.tintri_api import Tintri

logger = ThreadLogger(__name__)


def should_display(*args, **kwargs):
    """
    This action is exposed in the Tintri extension tab
    Should never be added to the left panel on any server
    """
    return False


def run(job, server, **kwargs):
    snapshot_uuid = kwargs.get('snapshot_uuid')
    new_vm_name = kwargs.get('new_vm_name')
    set_progress(f"New vm '{new_vm_name} will be created by cloning from Tintri snapshot with uuid '{snapshot_uuid}")

    tintri = Tintri()
    session_id = tintri.get_session_id(None, save_to_self=True)
    set_progress(f"Calls to Tintri API will be using session ID: {session_id}")

    resp = tintri.clone_from_snapshot(
        server.tintri_vm_uuid, snapshot_uuid, new_vm_name
    )
    set_progress(f"Tintri API response: {resp}")

    if isinstance(resp, dict):
        if "code" in resp and resp["code"].startswith("ERR"):
            return "FAILURE", "", resp["message"]

