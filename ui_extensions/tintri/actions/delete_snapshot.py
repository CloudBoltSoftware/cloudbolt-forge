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
    set_progress(f"Attempting to delete snapshot wiht uuid '{snapshot_uuid}' for server '{server}'")
    tintri = Tintri()
    session_id = tintri.get_session_id(None, save_to_self=True)
    set_progress(f"Calls to Tintri API will be using session ID: {session_id}")


    resp = tintri.delete_snapshot(snapshot_uuid)
    set_progress(f"Tintri API response: {resp}")