"""
Take snapshot action for AWS RDS DB Cluster.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
import boto3
import time
from django.db import IntegrityError

def run(job, resource, **kwargs):
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_cluster_identifier = resource.attributes.get(field__name='db_cluster_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)
    db_cluster_snapshot_identifier = '{{ db_cluster_snapshot_identifier }}'

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Creating a snapshot for "{}"'.format(db_cluster_identifier))

    rds.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier=db_cluster_snapshot_identifier,
        DBClusterIdentifier=db_cluster_identifier,
    )

    return "SUCCESS", "Cluster has succesfully been created", ""