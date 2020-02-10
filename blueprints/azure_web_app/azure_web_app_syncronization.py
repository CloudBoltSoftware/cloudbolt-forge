from common.methods import set_progress

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler

RESOURCE_IDENTIFIER = "azure_web_app_id"


def _get_clients(handler):
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
        resource_client = wrapper.resource_client
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id,
        )
        web_client = WebSiteManagementClient(credentials, handler.serviceaccount)
        resource_client = ResourceManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return web_client, resource_client


def discover_resources(**kwargs):
    discovered_web_apps = []
    for handler in AzureARMHandler.objects.all():

        web_client, resource_client = _get_clients(handler)

        for groups in resource_client.resource_groups.list():
            for web_app in web_client.web_apps.list_by_resource_group(
                resource_group_name=groups.name
            ):
                discovered_web_apps.append(
                    {
                        "name": web_app.name,
                        "azure_web_app_id": web_app.id,
                        "azure_web_app_name": web_app.name,
                        "azure_location": web_app.location,
                        "azure_web_app_default_host_name": web_app.default_host_name,
                        "resource_group_name": web_app.resource_group,
                    }
                )

    return discovered_web_apps
