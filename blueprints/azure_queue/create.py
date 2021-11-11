"""
Creates an Azure Queue.
"""
from typing import List

import settings

import azure.mgmt.storage as storage
from azure.mgmt.storage import StorageManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.storage.queue import QueueService

from common.methods import is_version_newer, set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.azure_arm.models import AzureARMHandler


cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.1")


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def get_azure_storage_client(handler) -> StorageManagementClient:
    """Return an Azure storage client with the Resource Handler details."""
    credentials = ServicePrincipalCredentials(
        client_id=handler.client_id, secret=handler.secret, tenant=get_tenant_id_for_azure(handler),
    )
    client = storage.StorageManagementClient(credentials, handler.serviceaccount)
    return client


def generate_options_for_env_id(server=None, **kwargs) -> List:
    """Dynamically generate values for the Environments for the form field based on the Azure Resource Technology type."""
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs) -> List:
    """Dynamically generate options for resource group form field based on the user's selection for Environment.
    
    This method requires the user to set the resource_group parameter as dependent on environment.
    """
    if control_value is None:
        return []

    env = Environment.objects.get(id=control_value)

    if CB_VERSION_93_PLUS:
        # Get the Resource Groups as defined on the Environment. The Resource Group is a
        # CustomField that is only updated on the Env when the user syncs this field on the
        # Environment specific parameters.
        resource_groups = env.custom_field_options.filter(
            field__name="resource_group_arm"
        )
        return [rg.str_value for rg in resource_groups]
    else:
        rh = env.resource_handler.cast()
        groups = rh.armresourcegroup_set.all()
        return [g.name for g in groups]


def generate_options_for_storage_account(control_value=None, **kwargs) -> List:
    """Dyanamically generate options for storage account form field based on the user's selection for Resource Group."""
    if control_value is None:
        return []

    storage_accounts = []

    for rh in AzureARMHandler.objects.all():
        # set_progress(f"Connecting To Azure Storage Service for Resource Handler {rh.name}...")
        azure_client = get_azure_storage_client(rh)

        storage_account_fnc = azure_client.storage_accounts.list_by_resource_group

        try:
            for account in storage_account_fnc(control_value):
                storage_accounts.append(account.name)
        # The exceptions cannot be seen as this method generates return values for
        # a web form dropdown. The return is either a list that contains a value,
        # or an empty list.
        except Exception:
            continue

    return storage_accounts


def create_custom_fields_as_needed() -> None:
    CustomField.objects.get_or_create(
        name="azure_storage_account_name",
        type="STR",
        defaults={
            "label": "Azure storage account Name",
            "description": "Storage account name where the file resides",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_storage_queue_name",
        type="STR",
        defaults={
            "label": "Azure file name",
            "description": "The given name for this file",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_account_key",
        type="STR",
        defaults={
            "label": "Azure Account Key",
            "description": "Used to authenticate this blueprint when making requests to Azure storage account",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_account_key_fallback",
        type="STR",
        defaults={
            "label": "Azure Account Key fallback",
            "description": "Used to authenticate this blueprint when making requests to Azure storage account",
            "show_as_attribute": True,
        },
    )


def run(job, **kwargs):
    resource = kwargs.get("resource")
    env_id = "{{ env_id }}"
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    resource_group = "{{ resource_group }}"
    create_custom_fields_as_needed()

    storage_account = "{{ storage_account }}"
    azure_queue_name = "{{ azure_queue_name }}"

    set_progress("Connecting To Azure Management Service...")
    azure_client = get_azure_storage_client(rh)

    res = azure_client.storage_accounts.list_keys(resource_group, storage_account)
    keys = res.keys
    set_progress("Connecting To Azure queues...")
    queue_service = QueueService(
        account_name="{{ storage_account }}", account_key=keys[0].value
    )

    set_progress("Creating a file...")
    if queue_service.exists(queue_name=azure_queue_name):
        return (
            "FAILURE",
            "Queue with this name already exists",
            "The queue can not be created.",
        )
    else:
        queue_service.create_queue("{{ azure_queue_name }}")
        resource.name = azure_queue_name
        resource.azure_storage_account_name = storage_account
        resource.azure_account_key = keys[0].value
        resource.azure_account_key_fallback = keys[1].value
        resource.azure_storage_queue_name = azure_queue_name
        resource.save()

    return "Success", "", ""
