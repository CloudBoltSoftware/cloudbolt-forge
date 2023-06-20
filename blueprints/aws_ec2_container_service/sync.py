"""
Build service item action for AWS EC2 Cluster Service blueprint.
"""
from infrastructure.models import Environment
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group


def connect_to_ecs(env):
    """
    Return boto connection to the ecs in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    if env.aws_region:
        client = wrapper.get_boto3_client(
            'ecs',
            rh.serviceaccount,
            rh.servicepasswd,
            env.aws_region
        )
        return client
    return None


RESOURCE_IDENTIFIER = ['cluster_name', 'aws_region']


def discover_resources(**kwargs):
    discovered_clusters = []
    disc_clusters = []

    environments = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services")

    bp = ServiceBlueprint.objects.filter(
        name__iexact="Amazon ECS").first()
    container_service_bp = ServiceBlueprint.objects.filter(
        name__iexact="Amazon ECS container service").first()
    group = Group.objects.filter(name__icontains='unassigned').first()
    resource_type = ResourceType.objects.filter(
        name__iexact="cluster").first()

    for environment in environments:
        ecs = connect_to_ecs(environment)
        if ecs:
            handler = environment.resource_handler.cast()

            try:
                clusters = ecs.list_clusters()
                for name in clusters['clusterArns']:
                    name = name.split('/')[1]
                    data = {
                        'name': name,
                        'cluster_name': name,
                        'aws_region': environment.aws_region,
                        'aws_rh_id': handler.id,
                    }
                    if data not in disc_clusters:
                        disc_clusters.append(data)
                        _ = dict(data)
                        _['env_id'] = environment.id

                        ecs_resource, _ = Resource.objects.get_or_create(
                            name=name,
                            blueprint=bp,
                            defaults={
                                "group": group,
                                "resource_type": resource_type
                            }
                        )
                        ecs_resource.env_id = environment.id
                        ecs_resource.cluster_name = name
                        ecs_resource.aws_region = environment.aws_region
                        ecs_resource.aws_rh_id = handler.id
                        ecs_resource.lifecycle = 'ACTIVE'
                        ecs_resource.save()

                        services = ecs.list_services(cluster=name)
                        for service in services['serviceArns']:
                            container_service_resource_type, _ = ResourceType.objects.get_or_create(
                                name="container_service")
                            service_name = service.split('/')[1]

                            service_resource, _ = Resource.objects.get_or_create(
                                name=service_name,
                                defaults={
                                    "group": group,
                                    "blueprint": container_service_bp,
                                    "resource_type": container_service_resource_type,
                                    "parent_resource": ecs_resource
                                }
                            )
                            service_response = ecs.describe_services(
                                cluster=name,
                                services=[
                                    service_name
                                ]
                            )
                            service_response = service_response.get('services')[0]
                            service_resource.desiredCount = service_response.get('desiredCount')
                            service_resource.runningCount = service_response.get('runningCount')
                            service_resource.status = service_response.get('status')
                            service_resource.launchType = service_response.get('launchType')
                            service_resource.lifecycle = 'ACTIVE'
                            service_resource.save()

                            discovered_clusters.append(_)

            except Exception as err:
                raise Exception(err)

    return []
