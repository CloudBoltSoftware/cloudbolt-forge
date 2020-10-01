from common.methods import generate_string_from_template_for_server, set_progress
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

    duration = kwargs.get('snapshot_duration')
    if duration >= 0:
        set_progress(f"Requested snapshot retention is {duration} minutes")
    else:
        set_progress("Requested snapshot will be set to never expire")

    tintri = Tintri()
    session_id = tintri.get_session_id(None, save_to_self=True)
    set_progress(f"Calls to Tintri API will be using session ID: {session_id}")

    snapshot_name_template = "{{ server.hostname }}-snapshot-00X"
    snapshot_name = generate_string_from_template_for_server(
        snapshot_name_template, server
    )

    resp = tintri.create_snapshot(
        "CRASH_CONSISTENT", kwargs.get( 'snapshot_duration'), snapshot_name, server.tintri_vm_uuid
    )
    set_progress(f"Tintri API response: {resp}")