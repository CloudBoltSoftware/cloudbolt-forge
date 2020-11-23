"""
Deletes an Azure storage file
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.storage.file import FileService

def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    file_name = resource.attributes.get(field__name='azure_storage_file_name').value
    share_name = resource.attributes.get(field__name='azure_storage_file_share_name').value
    azure_storage_account_name = resource.attributes.get(field__name='azure_storage_account_name').value
    azure_account_key = resource.attributes.get(field__name='azure_account_key').value

    set_progress("Connecting To Azure...")
    file_service = FileService(account_name=azure_storage_account_name, account_key=azure_account_key)

    set_progress("Connection to Azure established")


    set_progress("Deleting file %s..." % file_name)
    file_service.delete_file(file_name=file_name, share_name=share_name, directory_name='')

    return "Success", "The file has been deleted", ""