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


def run(resource, *args, **kwargs):
    env = Environment.objects.get(id=resource.env_id)
    taskDefinition = "{{ task_definition }}"
    launchType = "{{ launch_type }}"

    client = connect_to_ecs(env)

    try:
        client.run_task(
            cluster=resource.cluster_name,
            taskDefinition=taskDefinition,
            launchType=launchType
        )
    except Exception as error:
        return "FAILURE", "", f"{error}"

    return "SUCCESS", "", ""
