"""
Creates an MariaDB in Azure.
"""
from typing import List
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from azure.mgmt.rdbms import mariadb


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs) -> List:
    """Dynamically generate options for resource group form field based on the user's selection for Environment."""
    if control_value is None:
        return []

    # Get the environment
    env = Environment.objects.get(id=control_value)

    # Get the Resource Groups as defined on the Environment. The Resource Group is a
    # CustomField that is only updated on the Env when the user syncs this field on the
    # Environment specific parameters.
    resource_groups = env.custom_field_options.filter(field__name="resource_group_arm")

    return [rg.str_value for rg in resource_groups]


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            "label": "Azure RH ID",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_database_name",
        type="STR",
        defaults={
            "label": "Azure Database Name",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_server_name",
        type="STR",
        defaults={
            "label": "Azure Server Name",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_location",
        type="STR",
        defaults={
            "label": "Azure Location",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="resource_group_name",
        type="STR",
        defaults={
            "label": "Azure Resource Group",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )


def run(job, **kwargs):
    resource = kwargs.get("resource")
    create_custom_fields_as_needed()

    env_id = "{{ env_id }}"
    resource_group = "{{ resource_group }}"

    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress("Location: %s" % location)

    database_name = "{{ database_name }}"

    server_name = database_name + "-server"

    server_username = "{{ server_username }}"
    server_password = "{{ server_password }}"

    resource.name = "Azure MariaDB - " + database_name
    resource.azure_server_name = server_name
    resource.azure_database_name = database_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id, secret=rh.secret, tenant=rh.tenant_id,
    )
    client = mariadb.MariaDBManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure established")

    set_progress('Checking if server "%s" already exists...' % server_name)
    try:
        client.servers.get(resource_group, server_name)
    except CloudError as e:
        set_progress("Azure Clouderror: {}".format(e))
    else:
        # No ResourceNotFound exception; server already exists
        return (
            "FAILURE",
            "Database server already exists",
            "DB server instance %s exists already" % server_name,
        )

    set_progress('Creating server "%s"...' % server_name)
    params = {
        "location": location,
        "version": "12.0",
        "administrator_login": server_username,
        "administrator_login_password": server_password,
        "properties": {
            "create_mode": "Default",
            "administrator_login": server_username,
            "administrator_login_password": server_password,
        },
    }
    async_server_create = client.servers.create(resource_group, server_name, params,)
    async_server_create.result()

    set_progress(
        'Creating database "%s" on server "%s"...' % (database_name, server_name)
    )
    async_db_create = client.databases.create_or_update(
        resource_group, server_name, database_name, {"location": location}
    )
    database = async_db_create.result()  # Wait for completion and return created object
    assert database.name == database_name

    db = client.databases.get(resource_group, server_name, database_name)
    assert db.name == database_name

    set_progress('Database "%s" has been created.' % database_name)
