"""
Delete AWS Dynamo DB backup.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress

import boto3


def run(resource, **kwargs):
    region = resource.aws_region
    rh_id = resource.aws_rh_id
    backup_name = resource.backup_name
    backup_arn = resource.backup_arn

    handler = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon Dynamodb')

    dynamodb = boto3.client('dynamodb',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Deleting backup "{}"'.format(backup_name))

    try:
        dynamodb.delete_backup(
            BackupArn=backup_arn)

    except Exception as error:
        return "FAILURE", "", f"{error}"

    return "SUCCESS", "Backup has successfully been created", ""
