"""
Creates an Azure serverless function.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from common.methods import generate_string_from_template
import os, json


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_function_name', type='STR',
        defaults={'label': 'Azure function name', 'description': 'Name of a deployed azure function', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label': 'Azure Resource Group', 'description': 'Used by the Azure blueprints',
                  'show_as_attribute': True}
    )

def run(job, **kwargs):
    resource = kwargs.get('resource')
    function_name = '{{ function_name }}'
    storage_account_name = function_name + "storageaccount"
	file_location = "{{ file_location }}"
	if file_location.startswith(settings.MEDIA_URL):
        set_progress("Converting relative URL to filesystem path")
        file_location = file_location.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)

    create_custom_fields_as_needed()

    #check if function name is already in use
    function_name_check = "az functionapp list"
    val = os.popen(function_name_check).read()

    function_name_check_response = json.loads(val)
    used_names = []
    for function in function_name_check_response:
        used_names.append(function['name'])

    if function_name in used_names:
        response = "{0} function name is already in use. Please use a different one.".format(function_name)
        return "failure", response, ""

    #create a resource group for the fucntion
    resource_group_name = function_name + "-resource-group"
    resource_group_create = 'az group create --name ' + resource_group_name + ' --location westeurope'
    os.system(resource_group_create)

    #check if storage name is already in use, create a function storage
    name_check = "az storage account check-name --name {0}".format(storage_account_name)
    name_check_response = json.loads(os.popen(name_check).read())

    if name_check_response['nameAvailable']:
        create_storage_command = "az storage account create --name {0} --location westeurope --resource-group {1} --sku Standard_LRS".format(storage_account_name, resource_group_name)
        os.system(create_storage_command)
    else:
        return "failure", '{0}'.format(name_check_response['reason']), ""

    #create the azure function
    create_function_command = "az functionapp create --name " + function_name + " --storage-account " + storage_account_name + " --consumption-plan-location westeurope --resource-group " + resource_group_name
    try:
        create_fucntion_check = json.loads(os.popen(create_function_command).read())
    except Exception as e:
        return 'failure', 'the function app could not be created', '{0}'.format(e)


    if create_fucntion_check['name'] == function_name:
        set_progress('The function app has been succesfully created')
    else:
        return 'failure', 'The app could not be created', ''

    resource.name = function_name
    resource.resource_group_name = resource_group_name
    resource.save()

    fxn = "az functionapp deployment source config-zip -g {0} -n {1} --src {2}".format(resource_group_name, function_name, file_location)
    json.loads(os.popen(fxn).read())
    return 'success', 'The function has successfully been created.' , ''
