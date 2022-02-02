"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from datetime import datetime

RESOURCE_IDENTIFIER = 'azure_resource_id'

def discover_resources(**kwargs):

    discovered_instances = []

    for rh in AzureARMHandler.objects.all():

        try:
            wrapper = rh.get_api_wrapper()
        except Exception as e:
            set_progress(f"could not get wrapper: {e}")
            continue
        
        credentials = ServicePrincipalCredentials(
            client_id=rh.client_id,
            secret=rh.secret,
            tenant=rh.azure_tenant_id
        )

        set_progress('Connecting to Azure Databricks for handler: {}'.format(rh))

        resource_client = ResourceManagementClient(credentials, rh.serviceaccount)

        api_version = '2018-04-01'

        try:

            resources = resource_client.resources.get_by_id(f'/subscriptions/{rh.serviceaccount}/providers/Microsoft.Databricks/workspaces', api_version)

            for resource in resources.additional_properties['value']:
                rg_name = resource['id'].split('/')[4]
                rg_location = resource['location']

                instance = {
                    'name': resource['name'],
                    'region': rg_location,
                    'resource_group': rg_name,
                    'workspace_name': resource['name'],
                    'pricing_tier': resource['sku']['name'],
                    'disable_public_ip': resource['properties']['parameters']['enableNoPublicIp']['value'],
                    'azure_resource_id': resource['id'],
                    'azure_dbs_workspace_url': resource['properties']['workspaceUrl'],
                    'azure_api_version': api_version,
                }

                set_progress(instance)

                discovered_instances.append(instance)

        except Exception as e:
            set_progress(f"Exception: {e}")
            continue
    
    return discovered_instances