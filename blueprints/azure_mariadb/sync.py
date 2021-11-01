from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.rdbms import mariadb
from msrestazure.azure_exceptions import CloudError
import azure.mgmt.resource.resources as resources


RESOURCE_IDENTIFIER = "azure_database_name"


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def discover_resources(**kwargs):

    discovered_azure_sql = []
    for handler in AzureARMHandler.objects.all():
        set_progress(
            "Connecting to Azure sql \
        DB for handler: {}".format(
                handler
            )
        )
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=get_tenant_id_for_azure(handler),
        )
        azure_client = mariadb.MariaDBManagementClient(
            credentials, handler.serviceaccount
        )
        azure_resources_client = resources.ResourceManagementClient(  # noqa: F841
            credentials, handler.serviceaccount
        )

        for server in azure_client.servers.list()._get_next().json()["value"]:
            resource_group = server.get("id").split("/")[4]
            try:
                for db in azure_client.databases.list_by_server(
                    resource_group, server["name"]
                ):
                    if db.name in [
                        "information_schema",
                        "performance_schema",
                        "mariadb",
                    ]:
                        continue
                    discovered_azure_sql.append(
                        {
                            "name": "Azure MariaDB - " + db.name,
                            "azure_server_name": server["name"],
                            "azure_database_name": db.name,
                            "resource_group_name": resource_group,
                            "azure_rh_id": handler.id,
                        }
                    )
            except CloudError as e:
                set_progress("Azure Clouderror: {}".format(e))
                continue

    return discovered_azure_sql
