import time
from common.methods import set_progress

from xui.solar_winds.solar_winds_helper import SolarWindsManager
from xui.solar_winds.solar_winds_scripts import (INSTALL_WINDOWS_AGENT,
                                                 CENTOS, RED_HAT, UBUNTU)


def run(server, *args, **kwargs):
    set_progress("Starting Install SolarWinds agent process...")
    solar_winds = SolarWindsManager()
    rest_connection_info = solar_winds.get_connection_info()

    # Check if there is a line of sight to the solawinds server
    try:
        server.execute_script(script_contents=f'ping -c 1 {rest_connection_info.ip}')
    except Exception as error:
        set_progress(f"{error}")
        return "FAILURE", "Agent Not Installed", ""
    if server.os_family.get_base_name() == 'Linux':
        try:
            ci = solar_winds.get_connection_info()
            context = {'server': server, 'connection_info': ci}
            if server.os_family.name.lower() == 'centos':
                output = solar_winds.install_linux_agent(server, CENTOS, context)
            elif server.os_family.name.lower() == 'red hat':
                output = solar_winds.install_linux_agent(server, RED_HAT, context)
            elif server.is_ubuntu():
                output = solar_winds.install_linux_agent(server, UBUNTU, context)
            else:
                set_progress("Agent installation not supported on this linux type")
                return "FAILURE", "Agent Not Installed", ""

        except Exception as error:
            set_progress(f"{error}")
            return "FAILURE", "Agent Not Installed", ""
    elif server.is_windows():
        try:
            output = solar_winds.install_windows_agent(INSTALL_WINDOWS_AGENT,
                                                   {'server': server, 'connection_info': rest_connection_info})
        except Exception as error:
            set_progress(f"{error}")
            return "FAILURE", "Agent Not Installed", f"{error}"
    else:
        set_progress("The OS type is not currently supported.")
        return "FAILURE", "Agent Not Installed", "The OS type is not currently supported."

    if output.split('\r\n'):
        set_progress('Agent Installation process started successfully.'
                     ' This is not a guarantee that the Installation will be successful. ')

        """
        Wait until the server metrics are available 
        In order to complete the Job. Wait for 2 minutes before giving up in case no metrics are received
        """
        set_progress("Waiting for server metrics...")
        if not solar_winds.is_agent_installed(server.ip)[0]:
            time.sleep(120)

        if solar_winds.is_agent_installed(server.ip)[0]:
            set_progress("The agent was installed successfully.")
            return "SUCCESS", "Agent Installed", ""
        else:
            set_progress("The agent was not installed successfully."
                         "To troubleshoot, ensure this server has a line of sight to the SolarWinds "
                         "server. "
                         "i.e Ensure you can be able to ping the server."
                         " Also ensure this server credentials are setup correctly.")
            return "FAILURE", "Agent Not Installed", ""
