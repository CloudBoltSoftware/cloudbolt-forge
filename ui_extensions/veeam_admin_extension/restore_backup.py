import requests
import time
from xml.dom import minidom

from common.methods import set_progress
from xui.veeam.veeam_admin import VeeamManager


def run(server, *args, **kwargs):
        set_progress(f"Starting Veeam Backup restoration... ")
        veeam = VeeamManager()
        server_ci = veeam.get_connection_info()
        url = f'http://{server_ci.ip}:9399/api/vmRestorePoints/' + \
              kwargs.get('restore_point_href') + '?action=restore'
        session_id = veeam.get_veeam_server_session_id()
        header = {"X-RestSvcSessionId": session_id}

        response = requests.post(url=url, headers=header)
        task = minidom.parseString(response.content.decode('utf-8'))
        items = task.getElementsByTagName('Task')[0].attributes.items()
        restoration_url = [item for item in items if item[0] == 'Href'][0][-1]

        def check_state():

            response = requests.get(restoration_url, headers=header)

            dom = minidom.parseString(response.content.decode('utf-8'))
            state = dom.getElementsByTagName('State')[0]
            child = state.firstChild
            return child

        # Wait until the restoration to completed.

        while check_state().data == 'Running':
            # wait
            set_progress("Waiting for restoration to complete...")
            time.sleep(10)

        if check_state().data == 'Finished':
            set_progress("Server restoration completed successfully")
            return "SUCCESS", "Server restoration completed successfully", ""
        else:
            set_progress("Server restoration didn't complete successfully")
            return "FAILURE", "", "Server restoration didn't complete successfully"
