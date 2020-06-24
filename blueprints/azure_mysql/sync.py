import azure.mgmt.resource.resources as resources
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.rdbms import mysql
from msrestazure.azure_exceptions import CloudError

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


RESOURCE_IDENTIFIER = [
    "azure_database_name",
    "resource_group_name",
    "azure_server_name",
]


def _get_clients(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    """
    set_progress("Connecting to Azure...")

    import settings
    from common.methods import is_version_newer

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        mysql_client = configure_arm_client(wrapper, mysql.MySQLManagementClient)
        resource_client = wrapper.resource_client
    else:
        # TODO: Remove once versions <= 9.2.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        mysql_client = mysql.MySQLManagementClient(credentials, handler.serviceaccount)
        resource_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount
        )

    set_progress("Connection to Azure established")

    return mysql_client, resource_client


def discover_resources(**kwargs):

    discovered_azure_sql = []
    for handler in AzureARMHandler.objects.all():
        set_progress("Connecting to Azure sql DB for handler: {}".format(handler))
        current_locations = list(handler.current_locations())

        mysql_client, resource_client = _get_clients(handler)

        for server in mysql_client.servers.list()._get_next().json()["value"]:
            if server["location"] not in current_locations:
                set_progress(
                    f"Skipping server {server['name']} in location {server['location']}."
                )
                continue

            try:
                resource_group_name = (
                    server["id"].split("/resourceGroups/")[1].split("/")[0]
                )
                for db in mysql_client.databases.list_by_server(
                    resource_group_name, server["name"]
                ):
                    # Skip any db's that are db schema specific. We are only interested
                    # in db's that are added by the user. 
                    if db.name in [
                        "information_schema",
                        "performance_schema",
                        "mysql",
                        "sys",
                    ]:
                        continue
                    discovered_azure_sql.append(
                        {
                            "name": "Azure MySql - " + db.name,
                            "azure_server_name": server["name"],
                            "azure_database_name": db.name,
                            "resource_group_name": resource_group_name,
                            "azure_rh_id": handler.id,
                            "azure_location": server["location"],
                        }
                    )
            except CloudError:
                set_progress(
                    f"No databases found in Resource Group {resource_group_name} for server {server['name']}. Skipping."
                )
                continue

    return discovered_azure_sql
