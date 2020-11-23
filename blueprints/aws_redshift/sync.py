from common.methods import set_progress
from infrastructure.models import Environment
import boto3

RESOURCE_IDENTIFIER = 'cluster_name'


def connect_to_redshift(env):
    """
    Return boto connection to the redshift in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    return boto3.client(
        'redshift',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd)


def discover_resources(**kwargs):
    redshift_clusters = []
    found_clusters = []

    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services")

    for env in envs:
        if not env.aws_region:
            continue
        client = connect_to_redshift(env)
        try:
            response = client.describe_clusters().get('Clusters')
            if len(response) > 0:
                for res in response:
                    if res.get('NumberOfNodes') == 1:
                        cluster_type = 'single-node'
                    else:
                        cluster_type = 'multi-node'
                    data = {
                        'name': res.get('ClusterIdentifier'),
                        'cluster_name': res.get('ClusterIdentifier'),
                        'node_type': res.get('NodeType'),
                        'cluster_type': cluster_type,
                        'master_username': res.get('MasterUsername'),
                        'env_id': env.id
                    }
                    _ = {
                        'name': res.get('ClusterIdentifier'),
                        'node_type': res.get('NodeType'),
                        'master_username': res.get('MasterUsername'),
                    }
                    if _ not in found_clusters:
                        found_clusters.append(_)
                        redshift_clusters.append(data)

        except Exception as error:
            set_progress(error)
            continue

    return redshift_clusters
