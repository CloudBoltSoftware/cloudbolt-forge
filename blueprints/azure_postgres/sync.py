import azure.mgmt.resource.resources as resources
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.rdbms import postgresql
from msrestazure.azure_exceptions import CloudError

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler

RESOURCE_IDENTIFIER = "azure_database_name"


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
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        azure_client = postgresql.PostgreSQLManagementClient(
            credentials, handler.serviceaccount
        )
        azure_resources_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount
        )

        for resource_group in azure_resources_client.resource_groups.list():
            for server in azure_client.servers.list()._get_next().json()["value"]:
                try:
                    for db in azure_client.databases.list_by_server(
                        resource_group.name, server["name"]
                    ):
                        if db.name in [
                            "information_schema",
                            "performance_schema",
                            "postgres",
                        ]:
                            continue
                        discovered_azure_sql.append(
                            {
                                "name": server["name"],
                                "azure_server_name": server["name"],
                                "azure_database_name": db.name,
                                "resource_group_name": resource_group.name,
                                "azure_rh_id": handler.id,
                            }
                        )
                except CloudError as e:
                    set_progress("Azure CloudError: {}".format(e))
                    continue

    return discovered_azure_sql
