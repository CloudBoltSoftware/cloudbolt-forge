from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt import sql
from msrestazure.azure_exceptions import CloudError


RESOURCE_IDENTIFIER = "azure_database"


def _get_client(handler):
    """
    Get the client using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    """
    import settings
    from common.methods import is_version_newer

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        sql_client = configure_arm_client(wrapper, sql.SqlManagementClient)
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        sql_client = sql.SqlManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return sql_client


def discover_resources(**kwargs):
    discovered_azure_sql = []
    for handler in AzureARMHandler.objects.all():
        set_progress("Connecting to Azure sql DB for handler: {}".format(handler))

        sql_client = _get_client(handler)

        for server in sql_client.servers.list():
            try:
                for db in sql_client.databases.list_by_server(
                    server.as_dict()["id"].split("/")[-5], server.name
                ):
                    if db.name == "master":
                        continue
                    discovered_azure_sql.append(
                        {
                            "name": db.name,
                            "azure_database": db.id,
                            "azure_server_name": server.name,
                            "azure_database_name": db.name,
                            "resource_group_name": server.as_dict()["id"].split("/")[
                                -5
                            ],
                            "azure_rh_id": handler.id,
                            "azure_location": db.location,
                        }
                    )
            except CloudError as e:
                set_progress("Azure Clouderror: {}".format(e))
                continue

    return discovered_azure_sql
