"""
Tear down for an AWS RDS DB Cluster
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError
import boto3
import time

def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    db_cluster_identifier = resource.attributes.get(field__name='db_cluster_identifier').value
    handler = AWSHandler.objects.get(id=rh_id)
    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Deleting cluster "{}"'.format(db_cluster_identifier))

    try:
        rds.delete_db_cluster(
            DBClusterIdentifier=db_cluster_identifier,
            SkipFinalSnapshot=True
        )
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Cluster has succesfully been deleted", ""
