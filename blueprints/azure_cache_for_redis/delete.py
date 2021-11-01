"""
Delete a Redis cache for Azure.
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.redis import RedisManagementClient
from msrestazure.azure_exceptions import CloudError


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    redis_cache_name = resource.attributes.get(field__name='azure_redis_cache_name').value
    resource_group = resource.attributes.get(
        field__name='resource_group_name').value
    rh_id = resource.attributes.get(field__name='azure_rh_id').value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=get_tenant_id_for_azure(rh),
    )
    redis_client = RedisManagementClient(
        credentials,
        rh.serviceaccount
    )
    set_progress("Connection to Azure established")

    set_progress("Deleting redis cache %s from Azure..." % redis_cache_name)

    try:
        redis_client.redis.delete(resource_group, redis_cache_name).wait()
        set_progress("Deleted cache %s..." % redis_cache_name)
    except CloudError as e:
        set_progress('Azure Clouderror: {}'.format(e))
        return "FAILURE", "Redid cache could not be deleted"

    return "Success", "Cache has been succesfully deleted", ""