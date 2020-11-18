from xui.data_dog.data_dog_scripts import (DOWNLOAD_DATA_DOG_AGENT_WINDOWS,
                               INSTALL_DATADOG_AGENT_WINDOWS,
                               INSTALL_DATADOG_AGENT_LINUX,
                               CHECK_AGENT_STATUS_WINDOWS,
                               CHECK_AGENT_STATUS_LINUX,
                               )
from xui.data_dog.data_dog_helper import DataDog

from common.methods import set_progress


def run(server, *args, **kwargs):
    set_progress("Starting Install DataDog agent process...")
    data_dog = DataDog()
    api_key = data_dog.get_api_key()
    if server.is_windows():
        download_agent_result = data_dog.download_agent(
            DOWNLOAD_DATA_DOG_AGENT_WINDOWS, {}, server=server)
        if download_agent_result.strip('\r\n') == "Error occurred while trying to download the agent.":
            set_progress("Error occurred while trying to download the agent.")
        else:
            try:
                data_dog.install_agent(INSTALL_DATADOG_AGENT_WINDOWS, {
                        'api_key': api_key}, server=server, run_with_sudo=False)
            except Exception as error:
                set_progress(f"The following Error occurred while trying to install the agent {error}")
                return "FAILURE", "", f"{error}"
            try:
                agent_status = data_dog.check_agent_status(CHECK_AGENT_STATUS_WINDOWS, {}, server)
                if int([pid.strip() for pid in agent_status.split('\r\n') if pid.strip().split(' ')[0] == 'Pid:'][0].split(' ')[-1]):
                    set_progress("Agent is running")
                    server.datadog_installed = True
                    server.save()
                    return "SUCCESS", "", "Agent installed"
            except Exception as error:
                set_progress(f"The following Error occurred while trying to get the status of the agent. {error}")
                return "FAILURE", "", f"{error}"

    elif server.os_family.get_base_name() == 'Linux':
        try:
            data_dog.install_agent(INSTALL_DATADOG_AGENT_LINUX, {'api_key': api_key}, server=server, run_with_sudo=True)
        except Exception as error:
            set_progress(f"The following Error occurred while trying to install the agent. {error}")
            return "FAILURE", "", f"{error}"
        try:
            agent_status = data_dog.check_agent_status(CHECK_AGENT_STATUS_LINUX, {'api_key': api_key}, server=server)
            status = [status.strip() for status in agent_status.split('\n') if status.strip().split(':')[0] == 'Active']
            if status:
                set_progress(f"{status[0][:25]}. Initial metrics might take few minutes before showing up.")
                server.datadog_installed = True
                server.save()
                return "SUCCESS", "Agent Installed", ""
        except Exception as error:
            set_progress(f"The following Error occurred while trying to get the status of the agent. {error}")
            return "FAILURE", "", f"{error}"
    else:
        set_progress("Data Dog Agent can't be installed on this server.")
        return "FAILURE", "Agent Not Installed", "The OS type is not currently supported."
