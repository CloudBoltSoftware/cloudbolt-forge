"""
Build service item action for AWS Virtual Private Cloud (VPC)
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from resourcehandlers.models import ResourceNetwork
from resourcehandlers.aws.models import AWSHandler, AwsVpcSubnet
import boto3,json


def generate_options_for_rh_id(server=None, **kwargs):
    options = [(rh.id, rh.name) for rh in AWSHandler.objects.all()]
    return sorted(options, key=lambda tup: tup[1].lower())


def generate_options_for_aws_region(server=None, **kwargs):
    options = []
    for region in boto3.session.Session().get_available_regions('ec2'):
        label = region[:2].upper() + region[2:].title().replace('-', ' ')
        options.append((region, label))
    return sorted(options, key=lambda tup: tup[1].lower())

def generate_options_for_tenancy(server=None, **kwargs):
    return [('default', 'Default'), ('dedicated', 'Dedicated')]


def run(job, logger=None, **kwargs):

    rh = AWSHandler.objects.get(id='{{ rh_id }}')
    aws_region = '{{ aws_region }}'
    cidr_block = '{{ cidr_block }}'
    provide_ipv6 = bool('{{ provide_ipv6 }}')
    tenancy = '{{ tenancy }}'

    CustomField.objects.get_or_create(
        name='aws_rh_id', type='STR',
        defaults={'label':'AWS RH ID', 'description':'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label':'AWS Region', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='vpc_id', type='STR',
        defaults={'label':'AWS VPC ID', 'description':'Used by the AWS VPC blueprint', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='aws_subnet_id', type='STR',
        defaults={'label':'AWS subnet ID', 'description':'Used by the AWS VPC blueprint', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='env_id', type='INT',
        defaults={'label':'Environment ID', 'description':'Used by the AWS VPC blueprint'}
    )
    CustomField.objects.get_or_create(
        name='env_url', type='URL',
        defaults={'label':'Environment', 'description':'Used by the AWS VPC blueprint', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='vpc_cidr_block', type='STR',
        defaults={'label':'AWS VPC CIDR block', 'description':'Used by the AWS VPC blueprint', 'show_as_attribute':True}
    )

    set_progress('Connecting to AWS...')
    client = boto3.client(
        'ec2',
        region_name=aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Creating VPC @ %s...' % cidr_block)

    response = client.create_vpc(
        CidrBlock=cidr_block,
        AmazonProvidedIpv6CidrBlock=provide_ipv6,
        InstanceTenancy=tenancy
    )

    vpc_dict = response['Vpc']
    vpc_id = vpc_dict['VpcId']
    state = vpc_dict['State']

    set_progress('State: %s' % state)
    set_progress('VPC ID: %s' % vpc_id)

    set_progress('Creating subnet in AWS...')
    response = client.create_subnet(
        CidrBlock=cidr_block,
        VpcId=vpc_id
    )
    subnet_dict = response['Subnet']
    subnet_id = subnet_dict['SubnetId']
    set_progress('Created subnet: %s' % subnet_id)

    set_progress('Creating CloudBolt environment...')
    env_name = vpc_id  # For now use "vpc - xxxxxx" as the environment name.
    env = Environment.objects.create(name=env_name, resource_handler=rh)
    env.aws_region = aws_region
    env.vpc_id = vpc_id
    env.save()

    set_progress('Syncing the subnet from AWS into the environment...')
    rh.sync_subnets(env)

    resource = kwargs.get('resource')
    resource.name = vpc_id # NOTE: vpc_id starts with "vpc-"
    resource.aws_region = aws_region
    resource.aws_rh_id = rh.id
    resource.vpc_id = vpc_id
    resource.aws_subnet_id = json.dumps([subnet_id])
    resource.env_id = env.id
    resource.env_url = '/environments/%i' % env.id
    resource.vpc_cidr_block = cidr_block
    resource.save()

    return "", "", ""
