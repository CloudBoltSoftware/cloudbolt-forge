"""
Discover AWS RDS DB Clusters.
"""
import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

RESOURCE_IDENTIFIER = 'db_cluster_identifier'

def discover_resources(**kwargs):
    discovered_clusters = []

    for handler in AWSHandler.objects.all():
        for region in handler.current_regions():
            rds = boto3.client(
                'rds',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd
            )
            try:
                for cluster in rds.describe_db_clusters()['DBClusters']:
                    discovered_clusters.append({
                        'name': cluster['DBClusterIdentifier'],
                        'db_cluster_identifier': cluster['DBClusterIdentifier'],
                        'aws_rh_id': handler.id,
                        'aws_region': region,
                        'status': cluster['Status'],
                        'engine': cluster['Engine']
                    })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_clusters