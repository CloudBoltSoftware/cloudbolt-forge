from xui.data_dog.data_dog_helper import DataDog

from common.methods import set_progress


def run(server, *args, **kwargs):
    set_progress("Starting process to uninstall DataDog agent...")
    datadog_manager = DataDog()
    set_progress("Waiting for agent to be uninstalled...")
    success, message = datadog_manager.uninstall_agent(server)

    if success:
        server.datadog_installed = False
        server.save()
        return "SUCCESS", "Agent successfully uninstalled. The metrics will take a few minutes to stop showing up.", ""

    return "FAILURE", "Agent not uninstalled.", f"{message}"
