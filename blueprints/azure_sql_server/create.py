"""
Creates an Azure Sql Server
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from azure.mgmt.sql import SqlManagementClient


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure")
    options = [(env.id, env.name) for env in envs]
    return options


def generate_options_for_resource_group(control_value=None, **kwargs):
    if control_value is None:
        return []
    env = Environment.objects.get(id=control_value)
    rh = env.resource_handler.cast()
    groups = rh.armresourcegroup_set.all()
    return [g.name for g in groups]


def run(job, **kwargs):
    resource = kwargs.get('resource')

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress('Location: %s' % location)

    resource_group = '{{ resource_group }}'
    server_name = '{{ server_name }}'

    server_username = '{{ server_username }}'
    server_password = '{{ server_password }}'


    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label':'Azure RH ID', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_server_name', type='STR',
        defaults={'label':'Azure Server Name', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label':'Azure Location', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label':'Azure Resource Group', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    resource.name = server_name
    resource.azure_server_name = server_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id,
    )
    client = SqlManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure established")


    set_progress('Checking if server "%s" already exists...' % server_name)
    try:
        client.servers.get(resource_group, server_name)
    except CloudError as e:
        set_progress('Azure Clouderror: {}'.format(e))
    else:
        return "FAILURE", "SQL server already exists", "SQL server instance %s exists already" % server_name

    set_progress('Creating server "%s"...' % server_name)
    params = {
        'location': location,
        'version': '12.0',
        'administrator_login': server_username,
        'administrator_login_password': server_password,
        'properties': {'create_mode': 'Default', 'administrator_login': server_username, 'administrator_login_password': server_password,}
    }

    async_server_create = client.servers.create_or_update(
        resource_group,
        server_name,
        params,
    )

    server = async_server_create.result()
    assert server.name == server_name

    svr = client.servers.get(resource_group, server_name)
    assert svr.name == server_name

    set_progress('Server "%s" has been created.' % server_name)