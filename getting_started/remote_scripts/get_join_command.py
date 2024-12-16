"""
Runs a script against the controller node to get the join command for the
Kubernetes cluster.
"""
from c2_wrapper import create_custom_field
from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, resource=None, *args, **kwargs):
    logger.debug(f'kwargs: {kwargs}')
    join_script = get_join_command_script()
    server = resource.server_set.get(service_item__name="Controller")
    result = server.execute_script(script_contents=join_script)
    cf = create_custom_field("k8s_join_command", "k8s_join_command", "TXT")
    member_servers = resource.server_set.filter(service_item__name="Workers")
    for server in member_servers:
        server.set_value_for_custom_field(cf, result)
    return "SUCCESS", "", ""


def get_join_command_script():
    return """#!/bin/bash
cat /tmp/kubeadm_join_command.sh
"""
