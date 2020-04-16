"""
Upload a file to azure storage
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from resources.models import Resource
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.storage as storage
from azure.storage.file import FileService
from django.conf import settings
from pathlib import Path
import os
from utilities.exceptions import CloudBoltException

def generate_options_for_storage_account(server=None, **kwargs):
    discovered_az_stores = []
    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure Storage \
        for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id
        )
        azure_client = storage.StorageManagementClient(credentials, handler.serviceaccount)
        set_progress("Connection to Azure established")
        for st in azure_client.storage_accounts.list():
            discovered_az_stores.append(st.name)
    return discovered_az_stores

def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_storage_account_name', type='STR',
        defaults={'label':'Azure storage account Name', 'description':'Storage account name where the file resides', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_storage_file_share_name', type='STR',
        defaults={'label':'Azure share name', 'description':'Share where this files resides in', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_storage_file_name', type='STR',
        defaults={'label':'Azure file name', 'description':'The given name for this file', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_account_key', type='STR',
        defaults={'label':'Azure Account Key', 'description':'Used to authenticate this blueprint when making requests to Azure storage account', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_account_key_fallback', type='STR',
        defaults={'label':'Azure Account Key fallback', 'description':'Used to authenticate this blueprint when making requests to Azure storage account', 'show_as_attribute':True}
    )

def run(job, **kwargs):
    resource = kwargs.get('resource')
    create_custom_fields_as_needed()

    storage_account = '{{ storage_account }}'
    file_path = "{{ file }}"
    azure_storage_file_share_name = '{{ azure_storage_file_share_name }}'
    overwrite_files = {{ overwrite_files }}
    file_name = Path(file_path).name

    if file_path.startswith(settings.MEDIA_URL):
        set_progress("Converting relative URL to filesystem path")
        file_path = file_path.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)

    if not file_path.startswith(settings.MEDIA_ROOT):
        file_path = os.path.join(settings.MEDIA_ROOT, file_path)


    try:
        set_progress("Connecting To Azure...")
        account_key = Resource.objects.filter(name__icontains=storage_account)[0].azure_account_key
        fallback_account_key = Resource.objects.filter(name__icontains=storage_account)[0].azure_account_key_fallback
        file_service = FileService(account_name=storage_account, account_key=account_key)



        set_progress('Creating file share {file_share_name} if it doesn\'t already exist...'.format(file_share_name=azure_storage_file_share_name))
        file_service.create_share(share_name=azure_storage_file_share_name, quota=1)



        set_progress('Connecting to file share')
        file_name_on_azure = file_name
        count = 0
        while (not overwrite_files) and file_service.exists(share_name=azure_storage_file_share_name, file_name=file_name_on_azure, directory_name=''):
            count+=1
            file_name_on_azure = '{file_name}({duplicate_number})'.format(file_name=file_name, duplicate_number=count)
            set_progress('File with name already exists on given file share, testing new name: {new_name}'.format(new_name=file_name_on_azure))
            
        
        local_resource_name = azure_storage_file_share_name + '-' + file_name_on_azure
        if overwrite_files and file_service.exists(share_name=azure_storage_file_share_name, file_name=file_name_on_azure, directory_name=''):
            set_progress('File with name already exists on given file share, overwriting')
            old_resource_to_overwite = Resource.objects.filter(name=local_resource_name, lifecycle='ACTIVE').first()
            
            if old_resource_to_overwite:
                old_resource_to_overwite.delete()


        set_progress('Creating the file with name {file_name} on the Storage Account {storage_account} using the share named {share_name}'.format(file_name=file_name_on_azure,storage_account=storage_account,share_name=azure_storage_file_share_name))
        file_service.create_file_from_path(share_name=azure_storage_file_share_name, file_name=file_name_on_azure, directory_name='', local_file_path=file_path)
        os.remove(file_path)


        set_progress('Creating local storage resource named {resource_name}'.format(resource_name=local_resource_name))
        resource.name = local_resource_name
        resource.azure_storage_account_name = storage_account
        resource.azure_account_key = account_key
        resource.azure_account_key_fallback = fallback_account_key
        resource.azure_storage_file_share_name = azure_storage_file_share_name
        resource.azure_storage_file_name = file_name_on_azure
        resource.save()

        return "Success", "The File has succesfully been uploaded", ""
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        if resource:
            resource.delete()
        
        raise CloudBoltException("File could not be uploaded because of the following error: {error}".format(error=e))
