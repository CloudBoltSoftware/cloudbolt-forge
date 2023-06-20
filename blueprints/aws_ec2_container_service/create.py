"""
Build service item action for AWS EC2 Cluster Service blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField, Environment


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS EC2 Cluster Service RH ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='aws_region',
        defaults={
            "label": 'AWS EC2 Cluster Service RH ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='env_id',
        defaults={
            "label": 'AWS EC2 Cluster Service Environment ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='cluster_name',
        defaults={
            "label": 'AWS cluster name',
            "type": 'STR',
        }
    )


def run(resource, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    cluster_name = '{{ cluster_name }}'

    create_custom_fields()

    resource.name = cluster_name
    resource.cluster_name = cluster_name
    resource.aws_region = region
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.aws_rh_id = rh.id
    resource.env_id = env_id
    resource.save()

    set_progress('Connecting to Amazon EC2 Cluster Service')
    ecs = wrapper.get_boto3_client(
        'ecs',
        rh.serviceaccount,
        rh.servicepasswd,
        region
    )

    set_progress('Create EC2 Cluster Service cluster "{}"'.format(cluster_name))

    try:
        ecs.create_cluster(
            clusterName=cluster_name
        )
    except Exception as err:
        return "FAILURE", "", err

    return "SUCCESS", "Created service cluster successfully", ""
