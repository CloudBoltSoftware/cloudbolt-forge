"""
Create an aws load balancer in AWS.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from botocore.client import ClientError
import boto3
import time


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def generate_options_for_subnet1(control_value=None, **kwargs):
    if control_value is None:
        return []
    subnets = []
    env = Environment.objects.get(id=control_value)
    handler = env.resource_handler.cast()
    client = boto3.client(
        'ec2',
        region_name=env.aws_region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd,
    )
    all_subnets = client.describe_subnets()['Subnets']
    for subnet in all_subnets:
        subnets.append(subnet['SubnetId'])
    return subnets


def generate_options_for_subnet2(control_value=None, **kwargs):
    if control_value is None:
        return []
    subnets = []
    env = Environment.objects.get(id=control_value)
    handler = env.resource_handler.cast()
    client = boto3.client(
        'ec2',
        region_name=env.aws_region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd,
    )
    all_subnets = client.describe_subnets()['Subnets']
    for subnet in all_subnets:
        subnets.append(subnet['SubnetId'])
    return subnets


def generate_options_for_scheme(server=None, **kwargs):
    options = ['internet-facing', 'internal']
    return options


def generate_options_for_balancer_type(server=None, **kwargs):
    options = ['application', 'network']
    return options


def generate_options_for_iptype(server=None, **kwargs):
    options = ['ipv4', 'dualstack']
    return options


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={'label': 'AWS DB Cluster RH ID', 'type': 'STR',
                                    'description': 'Used by the AWS DB Cluster blueprint'}
    )

    CustomField.objects.get_or_create(
        name='load_balancer_name', defaults={'label': 'AWS database cluster identifier', 'type': 'STR',
                                             'description': 'AWS Load balancer name'}
    )

    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label': 'AWS Region',
                  'description': 'Used by the AWS blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='load_balancer_status', type='STR',
        defaults={'label': 'AWS Load balancer status',
                  'description': 'AWS Load balancer status', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='load_balancer_arn', type='STR',
        defaults={'label': 'AWS Load balancer arn',
                  'description': 'The Amazon Resource Name (ARN) of the load balancer.', 'show_as_attribute': False}
    )

    CustomField.objects.get_or_create(
        name='scheme', type='STR',
        defaults={'label': 'AWS Load balancer scheme',
                  'description': 'AWS Load balancer scheme.', 'show_as_attribute': False}
    )

    CustomField.objects.get_or_create(
        name='balancer_type', type='STR',
        defaults={'label': 'AWS Load balancer type',
                  'description': 'AWS Load balancer type.', 'show_as_attribute': False}
    )

    CustomField.objects.get_or_create(
        name='ipadresstype', type='STR',
        defaults={'label': 'AWS Load balancer ip adress type',
                  'description': 'AWS Load balancer ip adress type.', 'show_as_attribute': False}
    )

    CustomField.objects.get_or_create(
        name='subnet1', type='STR',
        defaults={'label': 'AWS Load balancer subnet1',
                  'description': 'AWS Load balancer subnet 1.', 'show_as_attribute': False}
    )

    CustomField.objects.get_or_create(
        name='subnet2', type='STR',
        defaults={'label': 'AWS Load balancer subnet2',
                  'description': 'AWS Load balancer subnet 2.', 'show_as_attribute': False}
    )


def run(job, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    handler = env.resource_handler.cast()

    balancer_name = '{{ name }}'
    scheme = "{{ scheme }}"
    balancer_type = "{{ balancer_type }}"
    iptype = "{{ iptype }}"
    subnet1 = "{{ subnet1 }}"
    subnet2 = "{{ subnet2 }}"

    if subnet1 == subnet2:
        return "FAILURE", "subnet 1 must be different from subnet 2", "",

    create_custom_fields_as_needed()

    resource = kwargs.pop('resources').first()
    resource.name = balancer_name
    resource.load_balancer_name = balancer_name
    resource.aws_region = region
    resource.aws_rh_id = handler.id
    resource.save()

    set_progress('Connecting to Amazon RDS')
    client = boto3.client('elbv2',
                          region_name=region,
                          aws_access_key_id=handler.serviceaccount,
                          aws_secret_access_key=handler.servicepasswd
                          )

    set_progress('Creating load balancer "{}"'.format(balancer_name))
    try:
        response = client.create_load_balancer(
            Name=balancer_name,
            Scheme=scheme,
            Type=balancer_type,
            IpAddressType=iptype,
            Subnets=[
                subnet1, subnet2
            ]
        )
        state = response['LoadBalancers'][0]['State']['Code']
        load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']
        resource.load_balancer_status = state
        resource.load_balancer_arn = load_balancer_arn
        resource.scheme = scheme
        resource.balancer_type = balancer_type
        resource.ipadresstype = iptype
        resource.subnet1 = subnet1
        resource.subnet2 = subnet2
        resource.save()
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Cluster has succesfully been created", ""
