"""
Discover AWS DOC DB Clusters.
"""
import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

RESOURCE_IDENTIFIER = 'docdb_name'


def discover_resources(**kwargs):
    discovered_clusters = []

    for handler in AWSHandler.objects.all():
        for region in handler.current_regions():
            try:
                wrapper = handler.get_api_wrapper()
            except Exception:
                continue
            client = wrapper.get_boto3_client(
                'docdb',
                handler.serviceaccount,
                handler.servicepasswd,
                region
            )
            try:
                for cluster in client.describe_db_clusters()['DBClusters']:
                    if cluster['Engine'] == 'docdb':
                        discovered_clusters.append({
                            'name': cluster['DBClusterIdentifier'],
                            'docdb_name': cluster['DBClusterIdentifier'],
                            'aws_rh_id': handler.id,
                            'aws_region': region,
                            'status': cluster['Status'],
                            'engine': cluster['Engine']
                        })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_clusters
