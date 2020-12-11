import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment


RESOURCE_IDENTIFIER = 'backup_plan_name'

def discover_resources(**kwargs):
    discovered_security_groups = []    
    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon backup for handler: {}'.format(handler))
        for region in handler.current_regions():
            try:
                client = boto3.client('backup',
                        region_name=region,
                        aws_access_key_id=handler.serviceaccount,
                        aws_secret_access_key=handler.servicepasswd
                        )            
                for response in client.list_backup_plans()['BackupPlansList']:
                    discovered_security_groups.append({
                        "aws_region": region,
                        "aws_rh_id": handler.id,
                        "name": response['BackupPlanName'],
                        "backup_plan_name": response['BackupPlanName'],
                        "backup_plan_id": response['BackupPlanId'],
                    })
            except Exception as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue
            
    return discovered_security_groups