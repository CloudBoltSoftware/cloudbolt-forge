"""
Deletes an azure function
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from common.methods import generate_string_from_template
import os, json

def run(job, **kwargs):
    resource = kwargs.get('resource')
    function_name = resource.attributes.get(field__name='azure_function_name').value
    resource_group = resource.attributes.get(field__name='resource_group_name').value

    set_progress("Deleting function...")
    function_delete_command = "az functionapp delete --name {0} --resource-group {1}".format(function_name, resource_group)
    os.system(function_delete_command)

    return "Success", "The function has succefully been deleted.", ""