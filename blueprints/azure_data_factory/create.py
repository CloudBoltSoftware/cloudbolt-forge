"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import time
import requests
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import Factory

from common.methods import set_progress
from accounts.models import Group
from infrastructure.models import CustomField, Environment
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields():
    """
    Get or create custom fields
    """
    CustomField.objects.get_or_create(
        name="azure_region",
        type="STR",
        defaults={
            'label': "Region",
            'description': 'Location for all resources.',
            'required': True,
            'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name="resource_group",
        type="STR",
        defaults={
            'label': "Resource Group",
            'description': 'Used by the Azure blueprints',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="data_factory_name",
        type="STR",
        defaults={
            'label': "Name",
            'description': 'The name of the Azure Data factory to create, It should be unique.',
            'required': True,
            'placeholder': "Enter Data Factory Name"
        }
    )

    CustomField.objects.get_or_create(
        name="azure_resource_id",
        type="STR",
        defaults={
            'label': "Azure resoruce id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
            'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            'label': "Azure Resource Id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="configure_repository_type",
        type="STR",
        defaults={
            'label': "Configure Repository Type",
            'description': 'Git configuration - The hosting service of your repository',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="github_account_name",
        type="STR",
        defaults={
            'label': "Account Name",
            'description': 'Git configuration - Account Name (Azure DevOps account or GitHub account)',
            'required': True,
            'placeholder': "Enter GitHub/Azure DevOps Account Name"
        }
    )
    
    CustomField.objects.get_or_create(
        name="repository_branch_name",
        type="STR",
        defaults={
            'label': "Repository Branch Name",
            'description': 'Git configuration -The name of an existing branch that will be used for collaboration (usually master)',
            'required': True,
            'placeholder': "Enter existing branch name (E.g, master)"
        }
    )
    
    CustomField.objects.get_or_create(
        name="repository_name",
        type="STR",
        defaults={
            'label': "Repository Name",
            'description': 'Git configuration - The name of an existing Git repository, ex. myRepository.',
            'required': True,
            'placeholder': "Enter existing Git repository (E.g, myRepository)"
        }
    )
    
    CustomField.objects.get_or_create(
        name="repository_root_folder",
        type="STR",
        defaults={
            'label': "Repository Root Folder",
            'description': "Git configuration - Folder in the collaboration branch where Factory's entities will be stored. For ex: '/factorydata'. '/' would indicate the root folder.",
            'required': True,
            'placeholder': "Enter folder name where Factory's entities will be stored"
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_devops_project_name",
        type="STR",
        defaults={
            'label': "Project Namer",
            'description': "Git configuration -The Azure DevOps project name where the repo is located",
            'required': True,
            'placeholder': "Enter Azure DevOps project named"
        }
    )

def generate_options_for_azure_region(**kwargs):
    group_name = kwargs["group"]

    try:
        group = Group.objects.get(name=group_name)
    except Exception as err:
        return None
    
    # fetch all group environment
    envs = group.get_available_environments()

    options = [(env.id, env.name) for env in envs if env.resource_handler.resource_technology.name=="Azure"]
                    
    if not options:
        raise RuntimeError("No valid Environments on Azure resource handlers in CloudBolt")
        
    return options


def generate_options_for_resource_group(field, control_value=None, **kwargs):
    """
    Generate resource group options
    Dependency - azure region
    """
    options = []
    
    if not control_value:
        options.insert(0, ('', '--- First, Select an Region ---'))
        return options

    # get env object by id
    env = Environment.objects.get(id=control_value)
    
    # fetch all resource groups
    options = [(group.str_value, group.str_value) for group in  env.custom_field_options.filter(field__name='resource_group_arm')]

    if options:
        options = sorted(options, key=lambda tup: tup[1].lower())
        options.insert(0, ('', '--- Select Resource Group ---'))
    else:
        options.insert(0, ('', '--- No Resource Groups found in this Region ---'))
    
    return options
    

def generate_options_for_configure_repository_type(field, **kwargs):
    return [('', '--- Select Repo Type ---'), ('FactoryVSTSConfiguration', 'Azure DevOps'), ('FactoryGitHubConfiguration', 'GitHub')]
    
def _get_data_factory_client(rh):

    # initialize data factory client 
    adf_client = DataFactoryManagementClient(rh.get_api_wrapper().credentials, rh.serviceaccount)
    return adf_client
	
def deploy_data_factory(adf_client, **kwargs):
    """
    Deploy data factory on azure portal
    """
   
    try:
        # deploy data factory 
        dataFacotryObj = adf_client.factories.create_or_update(**kwargs)
    except Exception as err:
        raise RuntimeError(err)
	
    while dataFacotryObj.provisioning_state != 'Succeeded':
        
        # fetch data factory object
        dataFacotryObj = adf_client.factories.get(kwargs['resourceGroupName'], kwargs['factoryName'])
        
        time.sleep(10)
        
    return dataFacotryObj


def factory_repo_configuration(adf_client, dataFactoryObj, repo_configuration_kwargs):
    """
    To configure data factory repo(Github or Azure DevOps)
    configure_factory_repo(self, location_id, factory_resource_id, repo_configuration, custom_headers, raw, **operation_config)
    """

    logger.debug(f'Repo configuration params: {repo_configuration_kwargs}')
    
    try:
        # configure data factory repo 
        dataFactoryObj = adf_client.factories.configure_factory_repo(dataFactoryObj.location, dataFactoryObj.id, repo_configuration_kwargs)
    except Exception as err:
        raise RuntimeError(err)
    
    return dataFactoryObj


def validate_github_username(username):
    """
    Validate github username
    raise an error msg if it does not exist.
    """
    rsp = requests.get(f"https://api.github.com/users/{username}")
    
    if rsp.status_code != 200:
        raise RuntimeError(f"Invalid github username: {username}")

        
def run(job, *args, **kwargs):
    set_progress("Starting Provision of the data factory template...")
    
    resource = kwargs.get('resource')
    
    region = "{{azure_region}}"  # drop down
    resource_group = "{{resource_group}}" # drop down
    name = "{{data_factory_name}}" # free text, names must start with a letter or a number, and can contain only letters, numbers, and the dash (-) character, length min=3 and max=63
    
    repository_type = '{{configure_repository_type}}' # drop down, data factory repo type, optional
    
    # update actual resource name
    resource.name = name
    resource.save()
    
    # get or create custom fields
    get_or_create_custom_fields()
    
    # Get environment object
    env = Environment.objects.get(id=region)
    
    # Get resource handler object
    rh = env.resource_handler.cast()
    
    # Create Parameter inputs dict
    params_dict = {
        "factory_name": name,
        "resource_group_name": resource_group,
        "factory": Factory(location=env.node_location)
    }
    
    repo_config_kwargs = None
    
    if repository_type != "":
        
        repository_root_folder = '{{repository_root_folder}}' # free text, dependency repository_type, show/hide based on repository_type selection
        
        if not repository_root_folder.startswith("/"):
            repository_root_folder = f'/{repository_root_folder}'
        
        repo_config_kwargs = {
            'type': repository_type,
            'account_name': '{{github_account_name}}', # free text, dependency repository_type, show/hide based on repository_type selection
            'repository_name': '{{repository_name}}', # free text, dependency repository_type, show/hide based on repository_type selection
            'collaboration_branch':'{{repository_branch_name}}', # free text, dependency repository_type, show/hide based on repository_type selection
            'root_folder': repository_root_folder
        }
        
        azure_project_name = '{{azure_devops_project_name}}' # free text, dependency repository_type, show/hide based on repository_type selection
        
        if repository_type == 'FactoryVSTSConfiguration':
            repo_config_kwargs['project_name'] = azure_project_name
        
        else:
            validate_github_username(repo_config_kwargs['account_name'])
        
        
    logger.debug(f'Submitting request for  Data Factor template. deployment_name: '
                 f'{name}, resource_group: {resource_group}')
    set_progress(f'Submitting Data Factory request to Azure.')
    
    # get data factory client object
    adf_client = _get_data_factory_client(rh)
    
    # deploy data factory on azure
    dataFactoryObj = deploy_data_factory(adf_client, **params_dict)
    
    if repo_config_kwargs is not None:
        set_progress(f'Start configuration of data factory repo.')
        logger.debug(f'Start configuration of data factory repo.')
        
        # configure data factory repo
        dataFactoryObj = factory_repo_configuration(adf_client, dataFactoryObj, repo_config_kwargs)
        
        resource.configure_repository_type = repository_type
        resource.github_account_name = dataFactoryObj.repo_configuration.account_name
        resource.repository_name = dataFactoryObj.repo_configuration.repository_name
        resource.repository_branch_name = dataFactoryObj.repo_configuration.collaboration_branch
        resource.repository_root_folder = dataFactoryObj.repo_configuration.root_folder
        
        if repository_type == 'FactoryVSTSConfiguration':
            resource.azure_devops_project_name = azure_project_name
    
    set_progress(f'Data factory created successfully')
    logger.debug(f'deployment info: {name}')
    
    resource.azure_rh_id = rh.id
    resource.data_factory_name = name
    resource.azure_region = env.node_location
    resource.azure_resource_id = dataFactoryObj.id
    resource.resource_group = resource_group
    resource.save()
    
    return "SUCCESS", "Data factory deployed successfully", ""