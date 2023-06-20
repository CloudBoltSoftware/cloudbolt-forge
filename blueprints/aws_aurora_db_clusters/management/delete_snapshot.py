"""
Delete snapshot action for AWS RDS DB snapshot.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
import boto3
import time
from django.db import IntegrityError

def generate_options_for_snapshot(server=None, **kwargs):
    resource = kwargs.get('resource')
    snapshots = []
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_cluster_identifier = resource.attributes.get(field__name='db_cluster_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)

    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    response = rds.describe_db_cluster_snapshots(
        DBClusterIdentifier=db_cluster_identifier,
    )

    snapshots.extend([snapshot['DBClusterSnapshotIdentifier'] for snapshot in response['DBClusterSnapshots']])
    if len(snapshots) == 0:
        return []
    return snapshots

def run(job, resource, **kwargs):
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    handler = AWSHandler.objects.get(id=rh_id)
    snapshot_identifier = '{{ snapshot }}'

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Deleting snapshot "{}"'.format(snapshot_identifier))

    rds.delete_db_cluster_snapshot(
        DBClusterSnapshotIdentifier=snapshot_identifier
    )

    return "SUCCESS", "Snapshot has succesfully been deleted", ""