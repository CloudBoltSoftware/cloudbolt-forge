"""
Tear down for an AWS load balancer
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError
import boto3
import time

def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    load_balancer_name = resource.attributes.get(field__name='load_balancer_name').value
    load_balancer_arn = resource.attributes.get(field__name='load_balancer_arn').value
    handler = AWSHandler.objects.get(id=rh_id)
    set_progress('Connecting to Amazon RDS')
    client = boto3.client('elbv2',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Deleting load balancer "{}"'.format(load_balancer_name))

    try:
        client.delete_load_balancer(
            LoadBalancerArn=load_balancer_arn,
        )
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Cluster has succesfully been deleted", ""