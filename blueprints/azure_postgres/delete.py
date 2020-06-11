"""
Deletes a Postgres in Azure
"""
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.rdbms import postgresql

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


def run(job, **kwargs):
    resource = kwargs.pop("resources").first()

    server_name = resource.attributes.get(field__name="azure_server_name").value
    database_name = resource.attributes.get(field__name="azure_database_name").value
    resource_group = resource.attributes.get(field__name="resource_group_name").value
    rh_id = resource.attributes.get(field__name="azure_rh_id").value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id, secret=rh.secret, tenant=rh.tenant_id
    )
    client = postgresql.PostgreSQLManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure established")

    set_progress("Deleting database %s from %s..." % (server_name, database_name))
    client.databases.delete(resource_group, server_name, database_name).wait()

    set_progress("Deleting server %s..." % server_name)
    client.servers.delete(resource_group, server_name).wait()

    return "", "", ""
