"""
Discover AWS load balancer.
"""
import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

RESOURCE_IDENTIFIER = 'load_balancer_name'


def discover_resources(**kwargs):
    discovered_load_balancers = []

    for handler in AWSHandler.objects.all():
        for region in handler.current_regions():
            client = boto3.client(
                'elbv2',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd
            )
            try:
                for balancer in client.describe_load_balancers()['LoadBalancers']:
                    discovered_load_balancers.append({
                        'name': balancer['LoadBalancerName'],
                        'load_balancer_name': balancer['LoadBalancerName'],
                        'aws_rh_id': handler.id,
                        'aws_region': region,
                        'load_balancer_status': balancer['State']['Code'],
                        'load_balancer_arn': balancer['LoadBalancerArn'],
                        'scheme': balancer['Scheme'],
                        'balancer_type': balancer['Type'],
                        'ipadresstype': balancer['IpAddressType'],
                        'subnet1': balancer['AvailabilityZones'][0]['SubnetId'],
                        'subnet2': balancer['AvailabilityZones'][1]['SubnetId'],
                    })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_load_balancers
