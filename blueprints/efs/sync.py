from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
from botocore.client import ClientError 
import boto3


RESOURCE_IDENTIFIER = 'efs_file_system_id'

def discover_resources(**kwargs):
    discovered_efs = []
    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon EC2 for handler: {}'.format(handler))
        for env in handler.current_regions():
            set_progress('Connecting to Amazon EC2 for region: {}'.format(env))
            client = boto3.client(
                'efs',
                region_name=env,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd,
            )
            try:
                for efs in client.describe_file_systems()['FileSystems']:
                    discovered_efs.append({
                            'name': efs['FileSystemId'],
                            'efs_file_system_id': efs['FileSystemId'],
                            "aws_rh_id": handler.id,
                            "aws_region": env,
                            "state": efs['LifeCycleState'],
                        })

            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_efs