from common.methods import set_progress

from xui.new_relic.new_relic_helper import NewRelicManager
from xui.new_relic.new_relic_scripts import (
    DOWNLOAD_NEW_RELIC_AGENT_FOR_WINDOWS,
    INSTALL_SCRIPT,
    INSTALL_AGENT_FOR_CENTOS,
    INSTALL_AGENT_FOR_UBUNTU
)


def run(server, *args, **kwargs):
    set_progress("Starting Install New Relic agent process...")
    new_relic_manager = NewRelicManager()
    if server.is_windows():
        try:
            download_agent_result = new_relic_manager.download_windows_agent(DOWNLOAD_NEW_RELIC_AGENT_FOR_WINDOWS, {},
                                                                             server)
            if download_agent_result.strip('\r\n') == "Error occurred while trying to download the agent.":
                set_progress("Error occurred while trying to download the agent.")
            else:
                # The download was successful we can proceed with installation.
                set_progress("Agent downloaded successfully")
                context = {'license_key': new_relic_manager.get_license_key()}
                new_relic_manager.install_agent_on_windows(INSTALL_SCRIPT, context, server)
                server.new_relic_agent_installed = True
                server.save()
                set_progress("Agent Installed successfully.")
                return "SUCCESS", "Agent Installed", ""
        except Exception as error:
            set_progress(f"The following error occurred while trying to install the agent. Error: {error}")
            return "FAILURE", "Agent Not Installed", ""

    elif server.os_family and server.os_family.get_base_name() == 'Linux':
        try:
            context = {'license_key': new_relic_manager.get_license_key()}
            if server.is_ubuntu():
                new_relic_manager.install_agent_on_linux(INSTALL_AGENT_FOR_UBUNTU, context, server)
            else:
                new_relic_manager.install_agent_on_linux(INSTALL_AGENT_FOR_CENTOS, context, server)
            server.new_relic_agent_installed = True
            server.save()
            set_progress("Agent Installed successfully.")
            return "SUCCESS", "Agent Installed", ""
        except Exception as error:
            set_progress(f"The following error occurred while trying to install the agent. \nError: {error}")
            return "FAILURE", "Agent Not Installed", ""
    else:
        set_progress(f" We currently don't support agent installation for this server/OS type.")
        return "FAILURE", "Agent Not Installed", ""
