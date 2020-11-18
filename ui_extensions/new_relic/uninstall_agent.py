from common.methods import set_progress

from xui.new_relic.new_relic_helper import NewRelicManager


def run(server, *args, **kwargs):
    set_progress("Starting Process to Uninstall New Relic agent...")
    new_relic_manager = NewRelicManager()
    success, message = new_relic_manager.uninstall_agent(server)
    if success:
        server.new_relic_agent_installed = False
        server.save()
        set_progress("Agent Uninstalled successfully.")
        return "SUCCESS", "Agent Uninstalled successfully.", ""
    else:
        set_progress(f"Agent could not be Uninstalled successfully. {message}")
        return "FAILURE", "", f"Agent could not be Uninstalled successfully. {message}"
