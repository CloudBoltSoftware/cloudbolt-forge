"""
This CloudBolt plug-in shows how to fetch context from a sub-blueprint that was
deployed in a previous step. 
"""
from common.methods import set_progress


def run(job, *args, **kwargs):
    web_server_ip = "{{blueprint_context.web_tier.web_server.server.ip}}"
    set_progress("The Web Server's IP address is {}".format(web_server_ip))
    # web_server_ip could now be used to configure other tiers or external
    # systems.
    return "SUCCESS", "Successfully fetched the Web Server's IP", ""