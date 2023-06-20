"""
Discover Azure storage files
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.storage as storage
import azure.mgmt.resource.resources as resources
from azure.storage.file import FileService
from azure.storage.file.models import File
from msrestazure.azure_exceptions import CloudError


RESOURCE_IDENTIFIER = 'azure_file_identifier'

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id

def discover_resources(**kwargs):
    discovered_azure_sql = []
    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure storage \
        files for handler: {}'.format(handler))
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
            try:
                for st in azure_client.storage_accounts.list_by_resource_group(resource_group.name)._get_next().json()['value']:
                    res = azure_client.storage_accounts.list_keys(
                        resource_group.name, st['name'])
                    keys = res.keys
                    file_service = FileService(
                        account_name=st['name'], account_key=keys[1].value)
                    for share in file_service.list_shares():
                        for file in file_service.list_directories_and_files(share_name=share.name).items:
                            if type(file) is File:
                                data = {
                                    'name': share.name + '-' + file.name,
                                    'azure_storage_file_name': file.name,
                                    'azure_file_identifier': share.name + '-' + file.name,
                                    'resource_group_name': resource_group.name,
                                    'azure_rh_id': handler.id,
                                    'azure_storage_account_name': st['name'],
                                    'azure_account_key': keys[0].value,
                                    'azure_account_key_fallback': keys[1].value
                                }
                                discovered_azure_sql.append(data)
            except Exception as e:
                raise e
    return discovered_azure_sql