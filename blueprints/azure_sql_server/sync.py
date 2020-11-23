from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.sql import SqlManagementClient
from msrestazure.azure_exceptions import CloudError
import azure.mgmt.resource.resources as resources


RESOURCE_IDENTIFIER = 'azure_server_name'


def discover_resources(**kwargs):

    discovered_azure_sql = []
    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure sql \
        DB for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id
        )
        azure_client = SqlManagementClient(credentials, handler.serviceaccount)
        azure_resources_client = resources.ResourceManagementClient(credentials, handler.serviceaccount)

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for server in azure_client.servers.list_by_resource_group(resource_group.name)._get_next().json()['value']:
                    discovered_azure_sql.append(
                            {
                                'name': server['name'],
                                'azure_server_name': server['name'],
                                'resource_group_name': resource_group.name,
                                'azure_rh_id': handler.id
                            }
                        )
            except CloudError:
                continue

    return discovered_azure_sql