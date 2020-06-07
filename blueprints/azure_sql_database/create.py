"""
Creates an SQL database in Azure.
"""
from typing import List
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt import sql


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs) -> List:
    """Dynamically generate options for resource group form field based on the user's selection for Environment.
    
    This method requires the user to set the resource_group parameter as dependent on environment.
    """
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


def run(job, **kwargs):
    resource = kwargs.get("resource")
    create_custom_fields_as_needed()

    env_id = "{{ env_id }}"
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress("Location: %s" % location)

    resource_group = "{{ resource_group }}"

    database_name = "{{ database_name }}"

    server_name = database_name + "-server"

    server_username = "{{ server_username }}"
    server_password = "{{ server_password }}"

    sql_client = _get_client(rh)

    set_progress('Creating server "%s"...' % server_name)
    params = {
        "location": location,
        "version": "12.0",
        "administrator_login": server_username,
        "administrator_login_password": server_password,
    }
    async_server_create = sql_client.servers.create_or_update(
        resource_group, server_name, params,
    )
    while not async_server_create.done():
        set_progress("Waiting for sql server account to be created...")
        async_server_create.wait(20)

    set_progress(
        'Creating database "%s" on server "%s"...' % (database_name, server_name)
    )
    async_db_create = sql_client.databases.create_or_update(
        resource_group, server_name, database_name, {"location": location}
    )
    # Wait for completion and return created object
    while not async_db_create.done():
        set_progress("Waiting for sql database account to be created...")
        async_db_create.wait(20)

    database = async_db_create.result()
    assert database.name == database_name

    db = sql_client.databases.get(resource_group, server_name, database_name)
    assert db.name == database_name

    resource.name = db.name
    resource.azure_server_name = server_name
    resource.azure_database_name = db.name
    resource.azure_database = db.id
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    set_progress('Database "%s" has been created.' % database_name)
