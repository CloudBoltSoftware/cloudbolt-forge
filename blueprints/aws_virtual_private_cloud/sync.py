from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
from botocore.client import ClientError
import boto3,json


RESOURCE_IDENTIFIER = 'vpc_id'


def discover_resources(**kwargs):
    aws_vpcs = []
    for handler in AWSHandler.objects.all():
        set_progress('Connecting to AWS for handler: {}'.format(handler))
        for env in handler.current_regions():
            set_progress(
                'Connecting to AWS regions for handler: {}'.format(handler))
            conn = boto3.client('ec2',
                                region_name=env,
                                aws_access_key_id=handler.serviceaccount,
                                aws_secret_access_key=handler.servicepasswd
                                )
            try:
                for aws_vpc in conn.describe_vpcs()['Vpcs']:                    
                    env_name = aws_vpc['VpcId']
                    environment, _ = Environment.objects.get_or_create(
                        name=env_name, resource_handler=handler)
                    subnets=[]
                    for subnet in conn.describe_subnets(Filters=[{'Name':'vpc-id','Values':[env_name]}])['Subnets']:
                        subnets.append(subnet['SubnetId'])
                    aws_vpcs.append({
                        "name": env_name,
                        "vpc_id": env_name,
                        "aws_subnet_id": json.dumps(subnets),
                        "aws_region": env,
                        "aws_rh_id": handler.id,
                        "env_id": environment.id,
                        "env_url": '/environments/%i' % environment.id
                    })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return aws_vpcs
