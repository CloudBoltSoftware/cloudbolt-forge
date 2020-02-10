"""
Deletes Web App from Azure
"""
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.web import WebSiteManagementClient
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


def _get_client(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    :param handler:
    :return:
    """
    import settings
    from common.methods import is_version_newer

    set_progress("Connecting To Azure...")

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        web_client = configure_arm_client(wrapper, WebSiteManagementClient)
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id,
        )
        web_client = WebSiteManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return web_client


def run(job, **kwargs):
    # Run as Resource teardown management command
    resource = job.resource_set.first()

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    handler = AzureARMHandler.objects.first()
    web_client = _get_client(handler)

    # Use custom field web_app_id to get web app from Azure
    rg = resource.attributes.get(field__name__startswith="resource_group_name")

    # Delete the web app
    web_client.web_apps.delete(
        resource_group_name=rg.value, name=resource.name, delete_empty_server_farm=False
    )
