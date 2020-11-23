"""
Creates an Redis cache for Azure.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from azure.mgmt.redis import RedisManagementClient
from azure.mgmt.redis.models import Sku, RedisCreateParameters


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

def generate_options_for_sku(server=None, **kwargs):
    return ['Basic', 'Standard', 'Premium']

def generate_options_for_capacity(control_value=None, **kwargs):
    if control_value:
        if control_value in ['Basic', 'Standard']:
            return [0, 1, 2, 3, 4, 5, 6]
        elif control_value == 'Premium':
            return [1, 2, 3, 4]

def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label':'Azure RH ID', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_redis_cache_name', type='STR',
        defaults={'label':'Azure Redis Cache Name', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label':'Azure Location', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label':'Azure Resource Group', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

def run(job, **kwargs):
    resource = kwargs.get('resource')
    create_custom_fields_as_needed()

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress('Location: %s' % location)

    resource_group_name = '{{ resource_group }}'
    redis_cache_name = '{{ redis_cache_name }}'
    sku = '{{ sku }}'
    capacity = '{{ capacity }}'

    resource.name = 'Azure redis cache - ' + redis_cache_name
    resource.azure_redis_cache_name = redis_cache_name
    resource.resource_group_name = resource_group_name
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id,
    )
    redis_client = RedisManagementClient(
        credentials,
        rh.serviceaccount
    )
    set_progress("Connection to Azure established")
        

    set_progress('Creating redis cache "%s"...' % redis_cache_name)
    if sku in ['Basic', 'Standard']:
        family = 'C'
    elif sku == 'Premium':
        family = 'P'

    try:
        async_cache_create = redis_client.redis.create(
            resource_group_name,
            redis_cache_name,
            RedisCreateParameters(
                sku=Sku(name=sku, family=family, capacity=capacity),
                location=location
            )
        )
    except CloudError as e:
        set_progress('Azure Clouderror: {}'.format(e))
        return "FAILURE", "%s Redis cache name provided is not valid or is not available for use" % redis_cache_name

    cache = async_cache_create.result()

    assert cache.name == redis_cache_name

    got_cache = redis_client.redis.get(resource_group_name, redis_cache_name)
    assert got_cache.name == redis_cache_name

    set_progress('Redis cache "%s" has been created.' % redis_cache_name)