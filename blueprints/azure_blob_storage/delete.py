"""
Deletes Blob Storage Account from Azure
"""
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.common.credentials import ServicePrincipalCredentials
import azure.mgmt.storage as storage


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    account_name = resource.attributes.get(
        field__name='azure_storage_blob_name').value
    resource_group = resource.attributes.get(
        field__name='resource_group_name').value
    rh_id = resource.attributes.get(field__name='azure_rh_id').value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting to azure storage service...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=get_tenant_id_for_azure(rh)
    )

    client = storage.StorageManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to azure Storage established")

    set_progress("Deleting blob storage account %s..." % account_name)
    client.storage_accounts.delete(resource_group, account_name)

    return "Success", "The blob storage account has been deleted", ""
