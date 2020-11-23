from infrastructure.models import Environment
import boto3

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


def run(resource, *args, **kwargs):
    env = Environment.objects.get(id=resource.env_id)
    client = connect_to_redshift(env)

    try:
        client.delete_cluster(
                ClusterIdentifier=resource.name,
                SkipFinalClusterSnapshot=True)

    except Exception as error:
        return "FAILURE", "", f"{error}"
    return "SUCCESS", "", ""
