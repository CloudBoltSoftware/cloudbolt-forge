from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
import azure.mgmt.storage as storage
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.resource.resources as resources
from accounts.models import Group
from servicecatalog.models import ServiceBlueprint

RESOURCE_IDENTIFIER = 'azure_container_id'

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id
    return handler.tenant_id
    
def discover_resources(**kwargs):
    containers = []
    
    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure storage \
        container for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=get_tenant_id_for_azure(handler)
        )
        azure_client = storage.StorageManagementClient(
            credentials, handler.serviceaccount)
        azure_resources_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount)

        for resource_group in azure_resources_client.resource_groups.list():
            for account in azure_client.storage_accounts.list_by_resource_group(resource_group.name)._get_next().json()['value']:
                try:    
                    for container in azure_client.blob_containers.list(resource_group_name=resource_group.name, account_name=account['name'])._get_next().json()['value']:
                        res = azure_client.storage_accounts.list_keys(
                        resource_group.name, account['name'])
                        keys = res.keys
                        containers.append(
                            {
                                'azure_container_id' : container['id'],
                                'azure_rh_id':handler.id,
                                'azure_account_name':account['name'],
                                'azure_container_name':container['name'],
                                'azure_account_key':keys[0].value,
                                'resource_group_name':resource_group.name,
                                'azure_location': account['location']
                            }
                        )
                except Exception as e:
                    set_progress("Azure Exception: {}".format(e))

    return containers