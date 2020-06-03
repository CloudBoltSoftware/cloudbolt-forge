"""
Creates an CosmosDB database in Azure.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from utilities.exceptions import CloudBoltException
import azure.mgmt.cosmosdb as cosmosdb


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
        cosmosdb_client = configure_arm_client(wrapper, cosmosdb.CosmosDB)
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        cosmosdb_client = cosmosdb.CosmosDB(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return cosmosdb_client


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )

    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs):
    """Dynamically generate options for the reosource_group parameter."""
    if control_value is None:
        return []
    env = Environment.objects.get(id=control_value)
    resource_groups_on_env = env.custom_field_options.filter(
        field__name="resource_group_arm"
    )
    return [rg.str_value for rg in resource_groups_on_env]


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
        name="azure_account_name",
        type="STR",
        defaults={
            "label": "Azure Account Name",
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
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress("Location: %s" % location)

    resource_group = "{{ resource_group }}"
    account_name = "{{ account_name }}"

    client = _get_client(rh)

    # Missing dataa
    server_params = {
        "location": location,
        "version": "12.0",
        "administrator_login": "mysecretname",
        "administrator_login_password": "HusH_Sec4et",
        "locations": [{"location_name": location}],
    }

    set_progress("Creating database %s..." % account_name)

    try:
        command = client.database_accounts.create_or_update(
            resource_group, account_name, server_params,
        )
    except CloudError as e:
        msg = """The Azure Cosmos DB API was not able to connect.
                                     Please verify that you listed a valid Account Name.
                                     The account name provided was {}.
                                     Please see the Azure docs for more information
                                     https://docs.microsoft.com/en-us/azure/templates/microsoft.documentdb/2015-04-01/databaseaccounts.
                                """.format(
            account_name
        )
        raise CloudBoltException(msg) from e

    while not command.done():
        set_progress("Waiting for database to be created...")
        command.wait(20)

    resource.name = "Azure CosmosDB - " + account_name
    resource.azure_account_name = account_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    # Verify that we can connect to the new database
    set_progress("Verifying the connection to the new database...")
    db = client.database_accounts.get(resource_group, account_name)  # noqa: F841
    set_progress("Database %s has been created." % account_name)
