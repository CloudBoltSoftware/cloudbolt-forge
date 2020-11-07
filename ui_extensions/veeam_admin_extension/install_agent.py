from common.methods import set_progress
from xui.veeam.veeam_admin import VeeamManager
from xui.veeam.veeam_scripts import INSTALL_LINUX, INSTALL_WINDOWS
from infrastructure.models import CustomField, Server

def run(server, *args, **kwargs):
    set_progress("Starting install Veeam agent process...")
    veeam = VeeamManager()
    if server.is_windows():
        try:
            output = veeam.install_agent(INSTALL_WINDOWS, {'server': server})
        except Exception as error:
            set_progress(f"The following error occurred while trying to install the agent. Error: {error}")
            return "FAILURE", "Agent not installed", f"{error}"

    elif server.os_family.get_base_name() == 'Linux':
        try:
            output = veeam.install_agent(INSTALL_LINUX, {'server': server})
        except Exception as error:
            set_progress(f"The following error occurred while trying to install the agent. Error: {error}")
            return "FAILURE", "Agent not installed", f"{error}"
    else:
        set_progress("Veeam Agent can't be installed on this server")
        return "FAILURE", "Agent not installed", "OS is currently not supported"

    output = output.split('\n')

    CustomField.objects.get_or_create(
        name='veeam_agent_id', type='STR',
        defaults={'label': 'Veeam Agent ID', 'description': 'Veeam Agent ID that has been installed',
                  'show_as_attribute': True})

    veeam_agent_id = [x.split(':')[-1].strip()
                      for x in output if x.split(':')[0].strip() == 'Id'][-1]
    if veeam_agent_id:
        server.veeam_agent_id = veeam_agent_id
        server.save()
        set_progress("Agent installed successfully")
        return "SUCCESS", "Agent Installed", ""
