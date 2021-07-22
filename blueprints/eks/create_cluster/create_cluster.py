"""
Build service item action for AWS EKS Cluster Service blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
import boto3
from botocore.exceptions import ClientError
import ast
import time


def get_boto_client(env_id=None, boto_service=''):
    if env_id is None:
        return None
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    client = boto3.client(boto_service,
                          region_name=env.aws_region,
                          aws_access_key_id=rh.serviceaccount,
                          aws_secret_access_key=rh.servicepasswd
                          )
    return client, env


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values_list("id", "name")
    return list(envs)


def generate_options_for_role_arn(control_value=None, server=None, **kwargs):
    options = []
    if control_value is None:
        return options

    client, _ = get_boto_client(control_value, 'iam')
    response = client.list_roles()
    roles = response['Roles']
    for role in roles:
        if role['AssumeRolePolicyDocument']['Statement'][0]['Principal'].get('Service','') == 'eks.amazonaws.com':
            options.append((role['Arn'], role['RoleName']))
    return options


def generate_options_for_subnets(control_value=None, server=None, **kwargs):
    options = []
    if control_value is not None:
        client, env = get_boto_client(control_value, 'ec2')
        response = client.describe_subnets(Filters=[
            {
                'Name': 'state',
                'Values': ['available']
            },
            {
                'Name': 'vpc-id',
                'Values': [env.vpc_id]
            }
        ])
        subnets = response['Subnets']
        for subnet in subnets:
            options.append(subnet['SubnetId'])
    return options


def generate_options_for_security_groups(control_value=None, server=None, **kwargs):
    options = []
    if control_value is not None:
        client, env = get_boto_client(control_value, 'ec2')
        response = client.describe_security_groups(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [env.vpc_id]
                }
            ]
        )
        sgs = response['SecurityGroups']
        for sg in sgs:
            options.append(sg['GroupId'])
    return options


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
            "show_as_attribute":True
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
        name='eks_subnets', type='STR',
        defaults={'label': 'AWS EKS subnets',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='eks_security_groups', type='STR',
        defaults={'label': 'AWS EKS cluster security groups',
                  'description': 'Used by the Amazon EKS blueprint', 'show_as_attribute': True}
    )


def run(resource, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    role_arn = '{{role_arn}}'
    security_groups = ast.literal_eval("{{security_groups}}")
    cluster_name = '{{ cluster_name }}'

    # Network Configuration
    subnets = ast.literal_eval("{{subnets}}")

    create_custom_fields()

    set_progress('Connecting to Amazon EKS')
    client, env = get_boto_client(env_id, 'eks')

    region = env.aws_region
    rh = env.resource_handler.cast()
    resource.name = cluster_name
    resource.cluster_name = cluster_name
    resource.aws_region = region
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.aws_rh_id = rh.id

    set_progress('Creating Amazon EKS cluster "{}" in "{}"'.format(cluster_name, region))
    set_progress(
        'Creating Amazon EKS cluster with role: "{}"'.format(role_arn))

    try:
        response = client.create_cluster(
            name=cluster_name,
            roleArn=role_arn,
            resourcesVpcConfig={
                'subnetIds': list(subnets),
                'securityGroupIds': list(security_groups)
            }
        )
        cluster = response['cluster']
        resource.lifecycle = 'ACTIVE'
        resource.eks_cluster_name = str(rh.id)+cluster['name']
        resource.arn = cluster['arn']
        resource.created_at = cluster['createdAt']
        resource.kubernetes_version = cluster['version']
        resource.role_arn = cluster['roleArn']
        resource.platform_version = cluster['platformVersion']
        resource.security_groups = cluster['resourcesVpcConfig']['securityGroupIds']
        resource.subnets=cluster['resourcesVpcConfig']['subnetIds']
        resource.vpc_id=cluster['resourcesVpcConfig']['vpcId']
        resource.save()

        # wait for cluster to be created. Check status every minutes
        while cluster['status'] == 'CREATING':
            set_progress('cluster "{}" is being created'.format(
                cluster_name))
            time.sleep(60)
            cluster_dict = client.describe_cluster(name=cluster_name)
            cluster = cluster_dict['cluster']
        # endpoint does not exist when cluster has not been created completely
        resource.endpoint = cluster['endpoint']
        resource.status = cluster['status']
        resource.lifecycle = 'ACTIVE'
        resource.save()
    except ClientError as e:
        resource.delete()
        set_progress('AWS ClientError: {}'.format(e))
        return "FAILURE", "", e
    except Exception as err:
        return "FAILURE", "Amazon EKS cluster could not be created", str(err)

    return "SUCCESS", "Created service cluster successfully", ""
