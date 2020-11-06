from common.methods import set_progress
from xui.veeam.veeam_admin import VeeamManager
from xui.veeam.veeam_scripts import RESTORE_TO_AZURE


def run(server, *args, **kwargs):
    set_progress(f"Starting Veeam Backup restoration... ")
    veeam_manager = VeeamManager()
    context = {}
    context.update(kwargs.get('script_context'))

    connection_info = veeam_manager.get_connection_info()
    context.update({'connection_info': connection_info})

    try:
        set_progress("Starting backup restoration to Azure. This might take a while...")
        result = veeam_manager.restore_backup_to_cloud(template=RESTORE_TO_AZURE, context=context)
        set_progress(f"Result from the backup restoration {result}")

    except Exception as error:
        set_progress("Error occurred while trying to restore backup to Azure")
        return "FAILURE", "", f"{error}"
