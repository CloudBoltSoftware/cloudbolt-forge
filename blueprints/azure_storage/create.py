"""
Creates an Azure Storage account.
"""
import settings

from azure.common.credentials import ServicePrincipalCredentials
import azure.mgmt.storage as storage
import azure.mgmt.storage.v2018_02_01.models as models

from common.methods import is_version_newer, set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment


cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.1")

def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs):
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


def generate_options_for_kind(server=None, **kwargs):
    # NOTE we are excluding v1 storage ('Storage') kind for simplicity.
    # It's now replaced by v2, and does not support the access tier
    # parameter - instead of dynamically hiding the access tier option,
    # we simply disable the v1 storage kind.
    # return ['Storage', 'StorageV2', 'BlobStorage']
    return ["StorageV2", "BlobStorage"]


def generate_options_for_sku_name(server=None, **kwargs):
    # Options for "Replication" and "Performance"
    return [
        "Standard_LRS",
        "Standard_GRS",
        "Standard_RAGRS",
        "Standard_ZRS",
        "Premium_LRS",
    ]


def generate_options_for_access_tier(server=None, **kwargs):
    return ["Hot", "Cool"]


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            "label": "Azure RH ID",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_account_name",
        type="STR",
        defaults={
            "label": "Azure Account Name",
            "description": "Used by the Azure blueprints",
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
            "label": "Azure Account Key",
            "description": "Used to authenticate this blueprint when making requests to Azure storage account",
            "show_as_attribute": False,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_location",
        type="STR",
        defaults={
            "label": "Azure Location",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="resource_group_name",
        type="STR",
        defaults={
            "label": "Azure Resource Group",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )


def _get_client(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2.1. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    """
    import settings
    from common.methods import is_version_newer

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2.1"):
        wrapper = handler.get_api_wrapper()
        storage_client = wrapper.storage_client
    else:
        # TODO: Remove once versions <= 9.2.1 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        storage_client = storage.StorageManagementClient(
            credentials, handler.serviceaccount
        )

    set_progress("Connection to Azure established")

    return storage_client


def run(job, **kwargs):
    resource = kwargs.get("resource")
    create_custom_fields_as_needed()

    env_id = "{{ env_id }}"
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location

    resource_group = "{{ resource_group }}"
    account_name = "{{ account_name }}"
    sku_name = "{{ sku_name }}"
    kind = "{{ kind }}"  # storageV2, storage, BlobStorage
    access_tier = "{{ access_tier }}"

    storage_client = _get_client(rh)

    # sku = models.Sku(name='Standard_LRS')
    sku = models.Sku(name=sku_name)

    parameters = models.StorageAccountCreateParameters(
        sku=sku, kind=kind, location=location, access_tier=access_tier
    )

    set_progress("Creating storage account %s..." % account_name)
    command = storage_client.storage_accounts.create(
        resource_group, account_name, parameters,
    )

    while not command.done():
        set_progress("Waiting for storage account to be created...")
        command.wait(20)

    # Verify that we can get info about the new storage account:
    set_progress("Verifying the connection to the new storage account...")
    properties = storage_client.storage_accounts.get_properties(
        resource_group, account_name
    )

    # Get and save accountkey
    res = storage_client.storage_accounts.list_keys(resource_group, account_name)
    set_progress("Checking keys")
    keys = res.keys

    resource.name = account_name
    resource.azure_account_name = account_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.azure_account_key = keys[0].value
    resource.azure_account_key_fallback = keys[1].value
    resource.save()

    if properties.name != account_name:
        # Should never happen
        return "FAILURE", "Failed to verify connection", "Failed to verify connection"

    set_progress(
        "Storage account %s has been created (%s)."
        % (account_name, properties.provisioning_state)
    )
