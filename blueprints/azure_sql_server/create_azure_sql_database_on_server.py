"""
2. Create Azure SQL database on the SQL server created on this service.

TODO: these params are no longer valid for the newer ARM API.
The following String type parameters are required by this action:
- azure_environment
- azure_sql_databases
- azure_sql_server_name: used to store the Azure-provided name on the service.
- azure_service_tier: Azure Options plugin generates 3 choices for this
  parameter (Basic, Standard, Premium)
- azure_performance_level: Azure Options plugin generates a number of options
  for this parameter. These are currently hard-coded in that plugin and can be
  changed there if desired.

Create these in Admin > Parameters. Also, import the Azure Options orchestration
action from the CB Content Library. This provides dropdown options for several
of these parameters, making a better experience for managers and end users.
"""
import json
from azure.mgmt.sql import SqlManagementClient

from common.methods import set_progress
from infrastructure.models import Environment
from orders.models import CustomFieldValue


def run(job, logger=None, **kwargs):
    """
    Action works as part of deploying a new service (blueprint action) and
    in ongoing management of services (service action).
    """
    set_progress('Creating SQL database...')

    service = job.service_set.first()

    # SQL server created in first plugin
    server_name = service.attributes.get(field__name='azure_sql_server_name').value

    # Runtime inputs
    database_name = '{{ database_name }}'
    service_tier = '{{ azure_service_tier }}'
    performance_level = '{{ azure_performance_level }}'

    set_progress("""
        Creating Azure SQL database "{database_name}"
            On SQL server: {server_name}
            Service Tier: {service_tier}
            Performance level: {performance_level}
        """.format(**locals()))

    options = get_blueprint_param_options()

    # Get the user's chosen environment
    env_id = get_param_value(options, 'azure_environment')
    env = Environment.objects.get(id=int(env_id))
    location = env.node_location
    set_progress('Azure environment: {}'.format(env))
    set_progress('    Node location: {}'.format(location))

    create_database(env, server_name, database_name)


def create_database(env, server_name, database_name)
    """
    Create an SQL Database on the SQL server

    Azure API docs for this operation:
    http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.mgmt.sql.operations.html#azure.mgmt.sql.operations.DatabasesOperations
    """
    rh = env.resource_handler.cast()
    sql_client = SqlManagementClient(rh.get_api_wrapper().credentials, rh.serviceaccount)

    response = sql_client.create_database(
        server_name,
        database_name,
        # Names for these settings in the Azure API do not match the Azure UI
        service_objective_id=performance_level,
        edition=service_tier,  # Optional: Basic, Standard, Premium, and Elastic
        # collation_name='',  # Optional
        # max_size_bytes='',  # Optional
    )

    save_db_info_on_service(service, database_name)


def save_db_info_on_service(service, database_name):
    # For ongoing management, save name of database on a special purpose service
    # attribute (a JSON string) that is a list of all databases on this sql
    # server.
    db_info = dict(
        name=database_name,
        service_tier=service_tier,
        performance_level=performance_level,
    )

    databases_cfv = service.attributes.filter(field__name='azure_sql_databases').first()
    if databases_cfv:
        # Remove old CFV to be replaced below
        set_progress('Removing old databases attribute from service')
        service.attributes.remove(databases_cfv)
        database_infos = json.loads(databases_cfv.value)
    else:
        set_progress('Creating new service attribute azure_sql_databases CFV')
        database_infos = []

    database_infos.append(db_info)
    database_infos_json = json.dumps(database_infos)
    set_progress('database_infos_json: {}'.format(database_infos_json))

    # Always get-or-create a CFV with our new value because we do not want to
    # modify CFV values: a CFV with that value may be in use by other services.
    databases_cfv, created = CustomFieldValue.objects.get_or_create(
        field__name='azure_sql_databases', value=database_infos_json)
    set_progress('databases_cfv created')

    service.attributes.add(databases_cfv)
    set_progress('databases_cfv added')

    return 'SUCCESS', '', ''


def create_sql_database(env, resource_group, server_name, database_name):
    """
    http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.mgmt.sql.models.html#azure.mgmt.sql.models.Database
    """
    set_progress('Create SQL database...')

    async_db_create = sql_client.databases.create_or_update(
        resource_group,
        server_name,
        database_name,
        {
            'location': env.node_location
        }
    )

    # Wait for completion and return created object
    database = async_db_create.result()
    set_logger('SQL database "{}" created:'.format(database_name))
    set_logger(database)
