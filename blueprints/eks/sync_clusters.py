from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
import boto3
from botocore.exceptions import ClientError
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group
from infrastructure.models import CustomField


RESOURCE_IDENTIFIER = 'eks_cluster_name'


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS RH ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='aws_region',
        defaults={
            "label": 'AWS Region ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='vpc_id',
        defaults={
            "label": 'AWS VPC ID',
            "type": 'STR',
            "show_as_attribute": True
        }
    )
    CustomField.objects.get_or_create(
        name='eks_cluster_name', type='STR',
        defaults={'label': 'AWS Cluster name',
                  'description': 'Used by the Amazon EKS blueprint'}
    )
    CustomField.objects.get_or_create(
        name='arn', type='STR',
        defaults={'label': 'ARN', 'description': 'Used by the Amazon EKS blueprint',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='created_at', type='STR',
        defaults={'label': 'Create At',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='kubernetes_version', type='STR',
        defaults={'label': 'Kubernetes version',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='endpoint', type='STR',
        defaults={'label': 'Amazon Cluster endpoint',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='status', type='STR',
        defaults={'label': 'status',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='role_arn', type='STR',
        defaults={'label': 'AWS Cluster role arn',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='platform_version', type='STR',
        defaults={'label': 'AWS EKS cluster platform version',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='subnets', type='STR',
        defaults={'label': 'AWS EKS subnets',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='security_groups', type='STR',
        defaults={'label': 'AWS EKS cluster security groups',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )


def discover_resources(**kwargs):
    create_custom_fields()
    for handler in AWSHandler.objects.all():
        set_progress(
            'Connecting to Amazon EKS for handler: {}'.format(handler))
        blueprint = ServiceBlueprint.objects.filter(
            name__icontains="amazon eks").first()
        resource_type = ResourceType.objects.filter(
            name__icontains="cluster").first()
        group = Group.objects.filter(name__icontains='unassigned').first()
        for region in handler.current_regions():
            set_progress(
                'Connecting to Amazon EKS for handler: {}'.format(handler))
            client = boto3.client('eks',
                                  region_name=region,
                                  aws_access_key_id=handler.serviceaccount,
                                  aws_secret_access_key=handler.servicepasswd,
                                  )
            try:
                response_dict = client.list_clusters()
                for cluster_name in response_dict['clusters']:
                    cluster_dict = client.describe_cluster(name=cluster_name)
                    cluster = cluster_dict['cluster']
                    resource = Resource.objects.filter(name=cluster['name']).first()
                    if resource is None:
                        resource = Resource.objects.create(
                            name=cluster['name'],
                            blueprint=blueprint,
                            group=group,
                            resource_type=resource_type,

                        )
                        set_progress(f"Creating new resource {cluster['name']}")
                    resource.aws_region = region
                    # Store the resource handler's ID on this resource so the teardown action
                    # knows which credentials to use.
                    resource.aws_rh_id = handler.id
                    resource.lifecycle = 'ACTIVE'
                    resource.eks_cluster_name = str(handler.id)+cluster['name']
                    resource.arn = cluster['arn']
                    resource.created_at = cluster['createdAt']
                    resource.kubernetes_version = cluster['version']
                    resource.endpoint = cluster['endpoint']
                    resource.role_arn = cluster['roleArn']
                    resource.status = cluster['status']
                    resource.platform_version = cluster['platformVersion']
                    resource.security_groups = cluster['resourcesVpcConfig']['securityGroupIds']
                    resource.subnets = cluster['resourcesVpcConfig']['subnetIds']
                    resource.vpc_id = cluster['resourcesVpcConfig']['vpcId']
                    resource.save()

            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return []
