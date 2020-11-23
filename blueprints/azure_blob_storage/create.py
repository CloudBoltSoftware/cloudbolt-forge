"""
Creates an Azure Blob Storage account.
"""
from django.contrib.admin.utils import flatten
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.storage as storage
import azure.mgmt.storage.v2018_02_01.models as models


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure")
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(server=None, **kwargs):
    resource_groups = []
    for handler in AzureARMHandler.objects.all():
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id
        )
        client = ResourceManagementClient(credentials, handler.serviceaccount)
        resource_groups.append(
            [item.name for item in client.resource_groups.list()])
    return flatten(resource_groups)


def generate_options_for_sku_name(server=None, **kwargs):
    return ['Standard_LRS', 'Standard_GRS', 'Standard_RAGRS', 'Standard_ZRS', 'Premium_LRS']


def generate_options_for_access_tier(server=None, **kwargs):
    return ['Hot', 'Cool']


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label': 'Azure RH ID',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_storage_blob_name', type='STR',
        defaults={'label': 'Azure Storage Blob Name',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label': 'Azure Location',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label': 'Azure Resource Group',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )


def run(job, **kwargs):
    resource = kwargs.get('resource')
    create_custom_fields_as_needed()

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location

    resource_group = '{{ resource_group }}'
    account_name = '{{ account_name }}'
    sku_name = '{{ sku_name }}'
    access_tier = '{{ access_tier }}'

    set_progress("Connecting To Azure Storage Service...")

    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id,
    )
    client = storage.StorageManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure storage established")

    sku = models.Sku(name=sku_name)

    parameters = models.StorageAccountCreateParameters(
        sku=sku, kind='BlobStorage', location=location, access_tier=access_tier)

    set_progress("Creating Blob storage %s..." % account_name)
    command = client.storage_accounts.create(
        resource_group,
        account_name,
        parameters,
    )

    while not command.done():
        set_progress("Waiting for Blob storage to be created...")
        command.wait(20)

    # Verify that the blob storage was created:
    set_progress("Verifying the blob storage was created...")
    try:
        client.storage_accounts.get_properties(resource_group, account_name)
    except Exception:
        return "FAILURE", "Failed to create the blob storage", ""

    resource.name = account_name
    resource.azure_storage_blob_name = account_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    set_progress("Blob Storage %s has been created." % account_name)
