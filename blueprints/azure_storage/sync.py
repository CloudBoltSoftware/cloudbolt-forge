"""
Discover Azure Storage Records
Return Azure Storage records identified by sku, handler_id and location
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
import azure.mgmt.storage as storage


RESOURCE_IDENTIFIER = "azure_account_name"


def _get_client(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than .1. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    """
    import settings
    from common.methods import is_version_newer

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, ".1"):
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


def discover_resources(**kwargs):

    discovered_az_stores = []
    for handler in AzureARMHandler.objects.all():
        set_progress(
            "Connecting to Azure Storage \
        for handler: {}".format(
                handler
            )
        )

        storage_client = _get_client(handler)
        for st in storage_client.storage_accounts.list():
            discovered_az_stores.append(
                {
                    "name": st.name,
                    "azure_rh_id": handler.id,
                    "azure_account_name": st.name,
                }
            )
    return discovered_az_stores
