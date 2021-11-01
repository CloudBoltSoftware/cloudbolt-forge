import settings
from common.methods import set_progress, is_version_newer
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
import azure.mgmt.storage as storage
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.storage.blob import BlockBlobService, PublicAccess
from resources.models import Resource
from infrastructure.models import CustomField

cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.2")

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id
    return handler.tenant_id

def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure")
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs):
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
        return list(rh.armresourcegroup_set.values_list('name',flat=True))


def generate_options_for_storage_accounts(control_value=None, **kwargs):
    storage_accounts = []
    if control_value is None or control_value == "":
        return []

    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure Storage for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=get_tenant_id_for_azure(handler)
        )
        azure_client = storage.StorageManagementClient(credentials, handler.serviceaccount)
        set_progress("Connection to Azure established")
        for st in azure_client.storage_accounts.list():
            storage_accounts.append(st.name)
    return storage_accounts

def generate_options_for_permissions(**kwargs):
    return [
        (PublicAccess.OFF, "Only the owner has access"),
        (PublicAccess.Blob, "Anonymous read access for the blobs"),
        (PublicAccess.Container, "Anonymous read access for containers and blobs ")]


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label': 'Azure RH ID', 'description': 'Used by the Azure blueprints'}
    )
    CustomField.objects.get_or_create(
        name='azure_account_name', type='STR',
        defaults={'label': 'Azure Account Name', 'description': 'Used by the Azure blueprints',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='azure_container_name', type='STR',
        defaults={'label': 'Azure Account Container Name', 'description': 'Used by the Azure blueprints',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='azure_account_key', type='STR',
        defaults={'label': 'Azure Account Key',
                  'description': 'Used to authenticate this blueprint when making requests to Azure storage account',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label': 'Azure Resource Group', 'description': 'Used by the Azure blueprints',
                  'show_as_attribute': True}
    )


def run(job, *args, **kwargs):
    create_custom_fields_as_needed()
    resource = kwargs.get('resource')
    env_id = '{{ env_id }}'
    resource_group = "{{ resource_group }}"
    storage_account = "{{ storage_accounts }}"
    permission = "{{ permissions }}"
    container_name = "{{container_name}}"

    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress('Location: %s' % location)

    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=get_tenant_id_for_azure(rh)
    )
    client = storage.StorageManagementClient(credentials, rh.serviceaccount)
    
    resource.name = container_name
    resource.azure_account_name = storage_account
    resource.azure_container_name = container_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.lifecycle = "ACTIVE"
    resource.azure_rh_id = rh.id
    # Get and save accountkey
    res = client.storage_accounts.list_keys(resource_group, storage_account)
    keys = res.keys

    resource.azure_account_key = keys[0].value
    resource.save()

    azure_account_key = resource.azure_account_key

    if azure_account_key:
        block_blob_service = BlockBlobService(account_name=storage_account, account_key=azure_account_key)
        set_progress(f"Creating container named '{container_name}' ...")

        result = block_blob_service.create_container(container_name.lower())

        if result:
            # PublicAccess.OFF is the default so act if this is not what has been selected.
            if permission != PublicAccess.OFF:
                set_progress(f"Setting access permissions for '{container_name}'")
                set_progress(permission)
                block_blob_service.set_container_acl(container_name, public_access=permission)

            return "SUCCESS", f"'{container_name}' created successfuly", ""
        else:
            return "FAILURE", f"'{container_name}' already exists.", ""

    return "FAILURE", f"You don't have the account key for '{storage_account}'.", ""