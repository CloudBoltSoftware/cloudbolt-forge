"""
Delete snapshot action for AWS MariaDB database snapshot.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resources.models import Resource
from botocore.client import ClientError
import boto3
import time

def generate_options_for_snapshots(server=None, **kwargs):
    resource = kwargs.get('resource')
    snapshots = []
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_identifier = resource.attributes.get(field__name='db_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)

    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    response = rds.describe_db_snapshots(
        DBInstanceIdentifier=db_identifier,
        SnapshotType='manual'
    )

    snapshots.extend([snapshot['DBSnapshotIdentifier'] for snapshot in response['DBSnapshots']])
    return snapshots

def run(job, resource, **kwargs):
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_identifier = resource.attributes.get(field__name='db_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)
    snapshot_identifier = '{{ snapshots }}'

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Deleting snapshot "{}"'.format(snapshot_identifier))

    try:
        response = rds.delete_db_snapshot(
            DBSnapshotIdentifier= snapshot_identifier,
        )
        Resource.objects.filter(name__iexact=snapshot_identifier).first().delete()
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Snapshot has succesfully been deleted", ""