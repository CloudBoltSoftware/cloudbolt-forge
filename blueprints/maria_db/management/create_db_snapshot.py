"""
Take snapshot action for AWS MariaDB database.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from botocore.client import ClientError
import boto3
import time

def run(job, resource, **kwargs):
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_identifier = resource.attributes.get(field__name='db_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)
    snapshot_identifier = '{{ snapshot_identifier }}'

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Creating a snapshot for "{}"'.format(db_identifier))
    try:
        rds.create_db_snapshot(
            DBSnapshotIdentifier= snapshot_identifier,
            DBInstanceIdentifier= db_identifier,
        )
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Cluster has succesfully been created", ""
