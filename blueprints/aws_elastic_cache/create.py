from infrastructure.models import CustomField, Environment
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
import boto3
import time


def connect_to_elasticache(env):
    """
    Return boto connection to the elasticache in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    return (rh.id, boto3.client(
        'elasticache',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd))


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='env_id', defaults={
            'label': 'Environment ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='name', defaults={
            'label': 'AWS ElastiCache', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='cluster_name', defaults={
            'label': 'AWS ElastiCache cluster_name', 'type': 'STR'
        }
    )
    CustomField.objects.get_or_create(
        name='engine', defaults={
            'label': 'AWS ElastiCache engine', 'type': 'STR',
            'description': 'The name of the cache engine to be used for this cluster'
        }
    )


def generate_options_for_aws_environment(profile=None, **kwargs):
    envs_this_user_can_view = Environment.objects_for_profile(profile)
    aws_handlers = AWSHandler.objects.all()
    aws_envs = envs_this_user_can_view.filter(
        resource_handler_id__in=aws_handlers)
    return [(env.id, env.name) for env in aws_envs]


def generate_options_for_engine(**kwargs):
    return ['memcached', 'redis']


def generate_options_for_cache_node_type(**kwargs):
    return [
        ('cache.t2.micro', 'T2 node - cache.t2.micro'),
        ('cache.t2.small', 'T2 node - cache.t2.small'),
        ('cache.t2.medium', 'T2 node - cache.t2.medium'),
        ('cache.m3.medium', 'M3 node - cache.m3.medium'),
        ('cache.m3.large', 'M3 node - cache.m3.large'),
        ('cache.m3.xlarge', 'M3 node - cache.m3.xlarge'),
        ('cache.m4.xlarge', 'M4 node - cache.m4.xlarge'),
        ('cache.m4.2xlarge', 'M4 node - cache.m4.2xlarge'),
        ('cache.m4.4xlarge', 'M4 node - cache.m4.4xlarge'),
        ('cache.m4.10xlarge', 'M4 node - cache.m4.10xlarge'),
        ('cache.t1.micro', 'T1 node(not recommended) - cache.t1.micro'),
        ('cache.m1.small', 'T1 node(not recommended) - cache.m1.small'),
        ('cache.m1.medium', 'T1 node(not recommended) - cache.m1.medium'),
        ('cache.m1.large', 'T1 node(not recommended) - cache.m1.large'),
        ('cache.m1.xlarge', 'T1 node(not recommended) - cache.m1.xlarge'),
        ('cache.c1.xlarge', 'C1 node(not recommended) - cache.c1.xlarge'),
        ('cache.r3.large', 'R3 node - cache.r3.large'),
        ('cache.r3.xlarge', 'R3 node - cache.r3.xlarge'),
        ('cache.r3.2xlarge', 'R3 node - cache.r3.2xlarge'),
        ('cache.r3.4xlarge', 'R3 node - cache.r3.4xlarge'),
        ('cache.r3.8xlarge', 'R3 node - cache.r3.8xlarge'),
        ('cache.r4.large', 'R4 node - cache.r4.large'),
        ('cache.r4.xlarge', 'R4 node - cache.r4.xlarge'),
        ('cache.r4.2xlarge', 'R4 node - cache.r4.2xlarge'),
        ('cache.r4.4xlarge', 'R4 node - cache.r4.4xlarge'),
        ('cache.r4.8xlarge', 'R4 node - cache.r4.8xlarge'),
        ('cache.r4.16xlarge', 'R4 node - cache.r4.16xlarge'),
        ('cache.m2.xlarge', 'M2 node - cache.m2.xlarge'),
        ('cache.m2.2xlarge', 'M2 node - cache.m2.2xlarge'),
        ('cache.m2.4xlarge', 'M2 node - cache.m2.4xlarge'),
    ]


def run(resource, *args, **kwargs):
    create_custom_fields_as_needed()

    cluster_name = "{{ cluster_name }}"
    engine = "{{ engine }}"
    CacheNodeType = "{{ cache_node_type }}"
    env = Environment.objects.get(id='{{ aws_environment }}')

    NumCacheNodes = "{{ num_cache_nodes }}"

    if engine == 'redis':
        NumCacheNodes = 1

    rh_id, client = connect_to_elasticache(env)

    try:
        client.create_cache_cluster(
            CacheClusterId=cluster_name,
            Engine=engine,
            CacheNodeType=CacheNodeType,
            NumCacheNodes=int(NumCacheNodes),
        )
        waiter = client.get_waiter('cache_cluster_available')
        waiter.wait(
            CacheClusterId=cluster_name
        )

    except Exception as error:
        return "FAILURE", "", f"{error}"

    while True:
        response = client.describe_cache_clusters(
            CacheClusterId=cluster_name)

        cache_instances = response['CacheClusters']
        if len(cache_instances) != 1:
            raise RuntimeError(
                "Multiple caches with thi name {0} identified. ".format(cluster_name))

        cache_instance = cache_instances[0]

        status = cache_instance['CacheClusterStatus']
        set_progress('Status of the cluster is: %s' % status)

        if status == 'available':
            set_progress('Cluster is now available on host')
            break
        time.sleep(5)

    resource.name = cluster_name
    resource.cluster_name = cluster_name
    resource.engine = engine
    resource.aws_rh_id = rh_id
    resource.env_id = env.id
    resource.save()

    return "SUCCESS", "", ""
