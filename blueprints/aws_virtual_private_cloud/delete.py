"""
Teardown service item action for AWS Virtual Private Cloud (VPC) blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
import boto3
import json
from botocore.client import ClientError


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    env_id = resource.env_id
    vpc_id = resource.vpc_id
    rh_id = resource.aws_rh_id
    region = resource.aws_region
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to AWS...')
    client = boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Deleting VPC %s and contents' % vpc_id)

    subnet_ids = json.loads(resource.aws_subnet_id)
    for subnet_id in subnet_ids:
        try:
            client.delete_subnet(SubnetId=subnet_id)
        except ClientError as e:
            set_progress('AWS ClientError: {}'.format(e))
            continue

    env = Environment.objects.get(id=env_id)
    env.vpc_id = None
    env.save()

    client.delete_vpc(VpcId=vpc_id)

    set_progress('Deleting CloudBolt environment...')

    env.delete()

    return "", "", ""
