from infrastructure.models import Environment, CustomField
from resources.models import Resource, ResourceType
from servicecatalog.models import ServiceBlueprint


def connect_to_ecs(env):
    """
    Return boto connection to the ecs in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    client = wrapper.get_boto3_client(
        'ecs',
        rh.serviceaccount,
        rh.servicepasswd,
        env.aws_region
    )
    return client


def generate_options_for_task_definition(resource, **kwargs):
    env = Environment.objects.get(id=resource.env_id)
    client = connect_to_ecs(env)
    res = client.list_task_definition_families()
    return res.get('families')


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='desiredCount',
        defaults={
            "label": 'AWS EC2 Cluster Service Desired count',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='status',
        defaults={
            "label": 'AWS EC2 Cluster Service status',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='runningCount',
        defaults={
            "label": 'AWS EC2 Cluster Service runningCount',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='launchType',
        defaults={
            "label": 'AWS EC2 Cluster Service launchType',
            "type": 'STR',
        }
    )


def run(resource, *args, **kwargs):
    create_custom_fields()
    env = Environment.objects.get(id=resource.env_id)
    service_name = "{{ service_name }}"
    task_definition = "{{ task_definition }}"
    desiredCount = int("{{ desired_count }}")

    client = connect_to_ecs(env)

    container_service_bp = ServiceBlueprint.objects.filter(
        name__iexact="Amazon ECS container service").first()

    try:
        service = client.create_service(
            cluster=resource.cluster_name,
            serviceName=service_name,
            taskDefinition=task_definition,
            desiredCount=desiredCount,
        )
        resource_type, _ = ResourceType.objects.get_or_create(
            name="container_service")

        ecs_resource, _ = Resource.objects.get_or_create(
            name=service_name,
            blueprint=container_service_bp,
            defaults={
                "group": resource.group,
                "resource_type": resource_type,
                "parent_resource": resource
            }
        )
        service_response = service.get('service')

        ecs_resource.desiredCount = service_response.get('desiredCount')
        ecs_resource.runningCount = service_response.get('runningCount')
        ecs_resource.status = service_response.get('status')
        ecs_resource.launchType = service_response.get('launchType')
        ecs_resource.lifecycle = 'ACTIVE'
        ecs_resource.save()

    except Exception as error:
        return "FAILURE", "", f"{error}"

    return "SUCCESS", "", ""
