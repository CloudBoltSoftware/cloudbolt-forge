from common.methods import set_progress
from infrastructure.models import CustomField
from common.methods import generate_string_from_template
import os, json

RESOURCE_IDENTIFIER = 'azure_function_name'


def discover_resources(**kwargs):

    discovered_azure_fucntions = []
    function_name_check = "az functionapp list"
    function_name_check_response = json.loads(os.popen(function_name_check).read())
    for function in function_name_check_response:
        discovered_azure_fucntions.append({
            'azure_function_name': function['name'],
            'resource_group_name': function['resourceGroup'],
        })


    return discovered_azure_fucntions