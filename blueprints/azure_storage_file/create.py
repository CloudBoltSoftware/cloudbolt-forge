"""
Upload a file to azure storage
"""
import os
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
import azure.mgmt.resource.resources as resources

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id

def get_storage_client_details(account_flag = False):
    keys = None
    discovered_az_stores = []
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
        azure_resources_client = resources.ResourceManagementClient(credentials, handler.serviceaccount)

        if account_flag:
            set_progress("Connection to Azure established")
            for st in azure_client.storage_accounts.list():
                discovered_az_stores.append(st.name)
            discovered_az_stores = sorted(discovered_az_stores)
            return discovered_az_stores

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for st in azure_client.storage_accounts.list_by_resource_group(resource_group.name)._get_next().json()['value']:
                    if st['name'] == "{{ storage_account }}":
                        res = azure_client.storage_accounts.list_keys(
                        resource_group.name, st['name'])
                        keys = res.keys
                        break
            except Exception as e:
                raise e
        return keys

def generate_options_for_storage_account(server=None, **kwargs):
    discovered_az_stores = get_storage_client_details(True)
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
    file = "{{ file }}"
    azure_storage_file_share_name = '{{ azure_storage_file_share_name }}'
    file_name = Path(file).name
    if file.startswith(settings.MEDIA_URL):
        set_progress("Converting relative URL to filesystem path")
        file = file.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)

    keys = get_storage_client_details()
    account_key, fallback_account_key = keys[0].value, keys[1].value

    set_progress("Connecting To Azure...")
    file_service = FileService(account_name=storage_account, account_key=account_key)

    set_progress('Creating a file share...')
    file_service.create_share(share_name=azure_storage_file_share_name, quota=1)
    
    file = os.path.join(settings.MEDIA_ROOT, file)
    set_progress('Creating a file...')
    if file_service.exists(share_name=azure_storage_file_share_name, file_name=file_name, directory_name=''):
        file_service.create_file_from_path(share_name=azure_storage_file_share_name, file_name=file_name, directory_name='', local_file_path=file)
        return "WARNING", "File with this name already exists", "The file will be updated."
    else:
        file_service.create_file_from_path(share_name=azure_storage_file_share_name, file_name=file_name, directory_name='', local_file_path=file)
        resource.name = azure_storage_file_share_name + '-' + file_name
        resource.azure_file_identifier = azure_storage_file_share_name + '-' + file_name
        resource.azure_storage_account_name = storage_account
        resource.azure_account_key = account_key
        resource.azure_account_key_fallback = fallback_account_key
        resource.azure_storage_file_share_name = azure_storage_file_share_name
        resource.azure_storage_file_name = file_name
        resource.save()
    return "Success", "The File has succesfully been uploaded", ""