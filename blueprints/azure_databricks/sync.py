"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler
from infrastructure.models import CustomField

RESOURCE_IDENTIFIER = 'azure_resource_id'
API_VERSION = '2018-04-01'


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
        name="workspace_name",
        type="STR",
        defaults={
            'label': "Workspace Name",
            'description': 'The name of the Azure Databricks workspace to create.',
            'required': True,
        }
    )

    CustomField.objects.get_or_create(
        name="pricing_tier",
        type="STR",
        defaults={
            'label': "Pricing Tier",
            'description': 'The pricing tier of workspace.',
            'required': True,
        }
    )

    CustomField.objects.get_or_create(
        name="disable_public_ip",
        type="BOOL",
        defaults={
            'label': "Disable Public IP",
            'description': 'Specifies whether to deploy Azure Databricks workspace with Secure Cluster Connectivity (No Public IP) enabled or not',
            'required': True,
        }
    )

    CustomField.objects.get_or_create(
        name="azure_resource_id",
        type="STR",
        defaults={
            'label': "Azure resoruce id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
            'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name="azure_deployment_id",
        type="STR",
        defaults={
            'label': "Azure deployment id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )

    CustomField.objects.get_or_create(
        name="azure_correlation_id",
        type="STR",
        defaults={
            'label': "Azure Databricks Correlation Id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
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
        name="azure_dbs_workspace_url",
        type="STR",
        defaults={
            'label': "Azure api version",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )

    CustomField.objects.get_or_create(
        name="azure_api_version",
        type="STR",
        defaults={
            'label': "Azure Databricks Workspace URL",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )


def discover_resources(**kwargs):
    discovered_instances = []

    try:
        get_or_create_custom_fields()
    except Exception as e:
        set_progress(f"Error creating custom fields : {e}")

    for rh in AzureARMHandler.objects.all():

        try:
            wrapper = rh.get_api_wrapper()
        except Exception as e:
            set_progress(f"could not get wrapper: {e}")
            continue

        set_progress(
            'Connecting to Azure Databricks for handler: {}'.format(rh))

        try:
            resources = wrapper.resource_client.resources.get_by_id(
                f'/subscriptions/{rh.serviceaccount}/providers/Microsoft.Databricks/workspaces', API_VERSION)

            for resource in resources.additional_properties['value']:
                rg_name = resource['id'].split('/')[4]
                rg_location = resource['location']

                instance = {
                    'name': resource['name'],
                    'azure_region': rg_location,
                    'azure_rh_id': rh.id,
                    'resource_group': rg_name,
                    'workspace_name': resource['name'],
                    'pricing_tier': resource['sku']['name'],
                    'disable_public_ip': resource['properties']['parameters']['enableNoPublicIp']['value'],
                    'azure_resource_id': resource['id'],
                    'azure_dbs_workspace_url': resource['properties']['workspaceUrl'],
                    'azure_api_version': API_VERSION,
                }

                set_progress(instance)

                discovered_instances.append(instance)

        except Exception as e:
            set_progress(f"Exception: {e}")
            continue

    return discovered_instances
