"""
1. Create Azure SQL Server instance

There are some prerequisites for this action. Ensure the following string
parameters exist:
- azure_environment: used to give users a choice of which env to deploy to.
- azure_sql_server_name: used to store the Azure-provided server instance name
  in CB.
"""
from azure.mgmt.sql import SqlManagementClient

from common.methods import set_progress
from infrastructure.models import Environment
from orders.models import CustomFieldValue


def run(job, logger=None, **kwargs):
    set_progress('Creating Azure SQL database server...')

    # Runtime inputs
    admin_login = '{{ admin_login }}'
    admin_password = '{{ admin_password }}'

    options = get_blueprint_param_options()

    # Get the user's chosen environment
    env_id = get_param_value(options, 'azure_environment')
    env = Environment.objects.get(id=int(env_id))
    location = env.node_location
    set_progress('Azure environment: {}'.format(env))
    set_progress('    Node location: {}'.format(location))
    rh = env.resource_handler.cast()

    # Create a resource group using the user's chosen name
    resource_group_name = get_param_value(options, 'azure_resource_group')
    create_resource_group(resource_group_name)

    azure_server = create_sql_server(location, resourc_group, server_name, admin_login, admin_password)

    # Store the SQL server name as an attribute on this new Service
    # so it can be used by subsequent actions
    server_name = get_param_value(options, 'server_name')
    new_sql_server_name, created = CustomFieldValue.objects.get_or_create(
        field__name='azure_sql_server_name', value=server_name)

    service = job.service_set.first()
    service.attributes.add(new_sql_server_name)
    service.save()

    return 'SUCCESS', '', ''

def get_blueprint_param_options():
    orig_order_item = job.parent_job.order_item
    return (orig_order_item.installserviceitemoptions_set
               .get(service_item__name=CREATE_SQL_SERVER_PSSI_NAME))


def get_param_value(options, param_name):
    return options.custom_field_values.get(field__name=param_name).value


def create_sql_server(location, resourc_group, server_name, admin_login, admin_password):
    """
    Create an Azure server.

    For API documentation about this call, see
    http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.mgmt.sql.operations.html#azure.mgmt.sql.operations.ServersOperations.create_or_update
    and
    http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.mgmt.sql.models.html#azure.mgmt.sql.models.Server
    """
    server = sql_client.servers.create_or_update(
        GROUP_NAME,
        SERVER_NAME,
        {
            'location': location,
            'version': '12.0',
            'administrator_login': admin_login,
            'administrator_login_password': admin_password,
        }
    )
    set_progress('Azure server "{}" created:'.format(server_name))
    set_progress(server)
