from common.methods import set_progress
from xui.cloudendure.cloudendure_admin import CloudEndureManager
from xui.cloudendure.cloudendure_scripts import INSTALL_WINDOWS_AGENT, INSTALL_LINUX_AGENT


def run(server, *args, **kwargs):
    set_progress("Starting install CloudEndure agent process...")
    cloud_endure_manager = CloudEndureManager()
    install_token = kwargs.get('install_token')
    cloud_endure_project = kwargs.get('cloud_endure_project')

    if server.is_windows():
        try:
            cloud_endure_manager.install_agent(
                INSTALL_WINDOWS_AGENT, {'agent_installation_token': install_token[0]}, server)
        except Exception as error:
            set_progress(error)
        try:
            if cloud_endure_manager.check_agent_status(server):
                set_progress("The agent was installed successfully.")
                server.cloud_endure_project = cloud_endure_project
                server.save()
                return "SUCCESS", "The agent was installed successfully.", ""
            else:
                set_progress("The agent was not installed successfully.")
                return "FAILURE", "Agent not installed", ""
        except Exception as error:
            set_progress(error)
            return "FAILURE", "", f"{error}"

    elif server.os_family.get_base_name() == 'Linux':
        try:
            cloud_endure_manager.install_agent(
                INSTALL_LINUX_AGENT, {'agent_installation_token': install_token[0]}, server)
        except Exception as error:
            set_progress(f"Error occurred while trying to install the agent. {error}")
        try:
            if cloud_endure_manager.check_agent_status(server):
                set_progress("The agent was installed successfully.")
                server.cloud_endure_project = cloud_endure_project
                server.save()
                return "SUCCESS", "The agent was installed successfully.", ""
            else:
                set_progress("The agent was not installed successfully.")

        except Exception as error:
            set_progress(f"The agent was not installed successfully. {error}")
            return "FAILURE", "", f"{error}"
    else:
        return "FAILURE", "CloudEndure Agent can't be installed on this server", ""
