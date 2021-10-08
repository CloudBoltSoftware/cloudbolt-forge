from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.redis import RedisManagementClient
from msrestazure.azure_exceptions import CloudError
import azure.mgmt.resource.resources as resources

RESOURCE_IDENTIFIER = 'azure_redis_cache_name'


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id
   

def discover_resources(**kwargs):

    discovered_caches = []
    for handler in AzureARMHandler.objects.all():

        set_progress("Connecting To Azure...")
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=get_tenant_id_for_azure(handler),
        )
        redis_client = RedisManagementClient(
            credentials,
            handler.serviceaccount
        )
        set_progress("Connection to Azure established")

        azure_resources_client = resources.ResourceManagementClient(credentials, handler.serviceaccount)

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for cache in redis_client.redis.list_by_resource_group(resource_group.name)._get_next().json()['value']:
                    discovered_caches.append(
                            {
                            'name': 'Azure redis cache - ' + cache['name'],
                            'azure_redis_cache_name': cache['name'],
                            'resource_group_name': resource_group.name,
                            'azure_rh_id': handler.id
                            }
                        )
            except CloudError as e:
                set_progress('Azure Clouderror: {}'.format(e))
                continue

    return discovered_caches