from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.datafactory import DataFactoryManagementClient
from infrastructure.models import CustomField
from datetime import datetime

from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

RESOURCE_IDENTIFIER = 'azure_resource_id'


def get_or_create_custom_fields():
    """
    Helper functions for main function to create custom field as needed
    """
    CustomField.objects.get_or_create(
        name="azure_region",
        type="STR",
        defaults={
            'label': "Region",
            'description': 'Location for all resources.',
            'required': True,
            'show_on_servers': True
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
            'label': "Azure resource id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
            'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            'label': "Azure resource handler id",
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
            'label': "Project Name",
            'description': "Git configuration -The Azure DevOps project name where the repo is located",
            'required': True,
            'placeholder': "Enter Azure DevOps project named"
        }
    )


def data_factory_model_to_dict(resource, handler):
    """
    Mapping field of resources with dictionary from main function
    """

    instance = {
        "name":resource.name,
        "azure_region": resource.location,
        "azure_rh_id": handler.id,
        "azure_resource_id": resource.id,
        "resource_group": resource.id.split('/')[4],
        "data_factory_name": resource.name,
    }

    # Mapping repository field if it's in resource
    if resource.repo_configuration is not None:
        instance["configure_repository_type"] = resource.repo_configuration.type
        instance["github_account_name"] = resource.repo_configuration.account_name
        instance["repository_name"] = resource.repo_configuration.repository_name
        instance["repository_branch_name"] = resource.repo_configuration.collaboration_branch
        instance["repository_root_folder"] = resource.repo_configuration.root_folder

        if resource.repo_configuration.type == 'FactoryVSTSConfiguration':
            instance["azure_devops_project_name"] = resource.repo_configuration.project_name

    set_progress("resource_data: {}".format(instance))
    return instance


def discover_resources(**kwargs):
    """
    The main function for this plugin
    """

    discovered_instances = []

    # Make sure the system is set up correctly
    try:
        get_or_create_custom_fields()
    except Exception as e:
        set_progress(f"Error creating custom fields : {e}")

    for handler in AzureARMHandler.objects.all():
        try:

            # fetching wrapper from handler
            wrapper = handler.get_api_wrapper()

        except Exception as e:
            set_progress(f"could not get wrapper: {e}")
            continue

        set_progress('Connecting to Azure Datafactory for handler: {}'.format(handler))

        # initialize data factory client as resource client
        resource_client = DataFactoryManagementClient(wrapper.credentials, handler.serviceaccount)

        # fetching resource from data factories
        for resource in resource_client.factories.list():
            
            # information of resources
            logger.info(
                f"fetching resource {resource.name} from datafactories of {handler} handler  "
            )
            
            discovered_instances.append(data_factory_model_to_dict(resource, handler))

    return discovered_instances