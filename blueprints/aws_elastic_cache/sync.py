from common.methods import set_progress
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


RESOURCE_IDENTIFIER = 'cluster_name'


def discover_resources(**kwargs):
    discovered_cache = []
    cache = []

    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services")

    for env in envs:
        if not env.aws_region:
            continue
        client = connect_to_elasticache(env)
        try:
            response = client.describe_cache_clusters()
            if len(response.get('CacheClusters')) > 0:
                res = response.get('CacheClusters')[0]
                data = {
                    'name': res.get('CacheClusterId'),
                    'cluster_name': res.get('CacheClusterId'),
                    'engine': res.get('Engine'),
                    'aws_rh_id': env.resource_handler_id,
                    'env_id': env.id,
                }
                _ = {
                    'cluster_name': res.get('CacheClusterId'),
                    'engine': res.get('Engine'),
                    'aws_rh_id': env.resource_handler_id,
                }
                if _ not in cache:
                    if data not in discovered_cache:
                        discovered_cache.append(data)
                        cache.append(_)
        except Exception as error:
            set_progress(error)
            continue
    return discovered_cache
