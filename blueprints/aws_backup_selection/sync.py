from django.contrib.admin.utils import flatten
import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment


RESOURCE_IDENTIFIER = 'selection_name'


def discover_resources(**kwargs):
    discovered_backup_selections = []
    for handler in AWSHandler.objects.all():
        set_progress(
            'Connecting to Amazon RDS for handler: {}'.format(handler))
        for region in handler.current_regions():
            backup_plan_ids = []
            backup_plans_client = boto3.client('backup',
                                               region_name=region,
                                               aws_access_key_id=handler.serviceaccount,
                                               aws_secret_access_key=handler.servicepasswd
                                               )
            backup_plan_ids.append([backup_plan_id.get(
                'BackupPlanId') for backup_plan_id in backup_plans_client.list_backup_plans().get('BackupPlansList')])
            client = boto3.client('backup',
                                  region_name=region,
                                  aws_access_key_id=handler.serviceaccount,
                                  aws_secret_access_key=handler.servicepasswd
                                  )
            try:
                for backup_plan_id in flatten(backup_plan_ids):
                    for backup_selection in client.list_backup_selections(BackupPlanId=backup_plan_id).get('BackupSelectionsList'):
                        discovered_backup_selections.append({
                            "name": backup_selection.get('SelectionName'),
                            "selection_name": backup_selection.get('SelectionName'),
                            "aws_region": region,
                            "aws_rh_id": handler.id,
                            "backup_plan_id": backup_selection.get('BackupPlanId'),
                            "iam_role_arn": backup_selection.get('IamRoleArn'),
                            "backup_selection_id": backup_selection.get('SelectionId'),
                        })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_backup_selections
