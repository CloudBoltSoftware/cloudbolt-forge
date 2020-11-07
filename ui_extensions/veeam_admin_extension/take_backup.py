from common.methods import set_progress
from xui.veeam.veeam_admin import VeeamManager
from xui.veeam.veeam_scripts import CREATE_BACKUP


def run(server, *args, **kwargs):
        set_progress("Starting the Veeam take backup process...")
        veeam = VeeamManager()
        ci = veeam.get_connection_info()
        result = veeam.take_backup(CREATE_BACKUP, {'server': server, 'veeam_server': ci})
        set_progress("Waiting for the backup process to complete...")
        if result.lower() == 'success':
            set_progress("Backup taken successfully")
            return "SUCCESS", "Backup taken successfully", ""
        else:
            set_progress("Backup not taken successfully")
            return "SUCCESS", "Backup not taken successfully", ""
