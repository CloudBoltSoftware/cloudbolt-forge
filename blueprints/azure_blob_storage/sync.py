"""
Discover Azure Block Storages
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.storage as storage
import azure.mgmt.resource.resources as resources

RESOURCE_IDENTIFIER = 'azure_storage_blob_name'


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def discover_resources(**kwargs):

    discovered_az_block_storages = []
    discovered_az_block_storage_names = []

    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure Block Storage \
        for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=get_tenant_id_for_azure(handler)
        )
        azure_blob_client = storage.StorageManagementClient(
            credentials, handler.serviceaccount)

        azure_resources_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount)

        set_progress("Connection to Azure established")
        for st in azure_blob_client.storage_accounts.list():
            if st.kind == 'BlobStorage':
                if st.name not in discovered_az_block_storage_names:
                    discovered_az_block_storage_names.append(st.name)
                    discovered_az_block_storages.append({
                        'name': st.name,
                        'azure_storage_blob_name': st.name,
                        'resource_group_name': st.id.split('/')[4],
                        'azure_location': st.primary_location,
                        'azure_rh_id': handler.id
                    })
    return discovered_az_block_storages
