from infrastructure.models import Environment

import boto3


def connect_to_elasticache(env):
    """
    Return boto connection to the elasticache in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    return boto3.client(
        'elasticache',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd)


def run(resource, *args, **kwargs):
    env = Environment.objects.get(id=resource.env_id)
    client = connect_to_elasticache(env)

    try:
        client.delete_cache_cluster(
            CacheClusterId=resource.name)
    except Exception as error:
        return "FAILURE", "", f"{ error }"

    return "SUCCESS", "The cache is being deleted", ""
