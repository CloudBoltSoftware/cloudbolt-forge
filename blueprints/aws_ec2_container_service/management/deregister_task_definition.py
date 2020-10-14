from infrastructure.models import Environment


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
    result = client.list_task_definitions(status='ACTIVE')

    task_definitions = result.get('taskDefinitionArns')
    return [task_definition.split('/')[-1] for task_definition in task_definitions]


def run(resource, *args, **kwargs):
    env = Environment.objects.get(id=resource.env_id)
    taskDefinition = "{{ task_definition }}"

    client = connect_to_ecs(env)

    try:
        client.deregister_task_definition(
            taskDefinition=taskDefinition,
        )
    except Exception as error:
        return "FAILURE", "", f"{error}"

    return "SUCCESS", "", ""
