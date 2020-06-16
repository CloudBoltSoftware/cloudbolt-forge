"""
Deletes a MySql in Azure
"""
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.rdbms import mysql

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


def _get_client(handler):
    """
    Get the client using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    """
    set_progress("Connecting to Azure...")

    import settings
    from common.methods import is_version_newer

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        mysql_client = configure_arm_client(wrapper, mysql.MySQLManagementClient)
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        mysql_client = mysql.MySQLManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return mysql_client


def run(job, **kwargs):
    resource = kwargs.pop("resources").first()

    server_name = resource.attributes.get(field__name="azure_server_name").value
    database_name = resource.attributes.get(field__name="azure_database_name").value
    resource_group = resource.attributes.get(field__name="resource_group_name").value
    rh_id = resource.attributes.get(field__name="azure_rh_id").value
    rh = AzureARMHandler.objects.get(id=rh_id)

    client = _get_client(rh)

    set_progress("Deleting database %s from %s..." % (server_name, database_name))
    client.databases.delete(resource_group, server_name, database_name).wait()

    set_progress("Deleting server %s..." % server_name)
    client.servers.delete(resource_group, server_name).wait()

    return "", "", ""
