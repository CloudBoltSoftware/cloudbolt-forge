"""
Restart an azure function.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from common.methods import generate_string_from_template
import os, json

def run(job, resource, **kwargs):
    function_name = resource.attributes.get(field__name='azure_function_name').value
    function_resource_group = resource.attributes.get(field__name='resource_group_name').value

    set_progress('Restarting the function...')

    try:
        restart_function_command = "az functionapp restart --name {0} --resource-group {1}".format(function_name, function_resource_group)
        os.system(restart_function_command)
    except Exception:
        return "FAILURE", "The function app could not be restarted", ""

    return "SUCCESS", "The function app was succesfully restarted.", ""