"""
Delete snapshot action for AWS RDS DB snapshot.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resources.models import Resource, ResourceType
from servicecatalog.models import ServiceBlueprint
from accounts.models import Group
import boto3
import time
from django.db import IntegrityError

def run(job, resource, **kwargs):
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

    set_progress('Getting all snapshots for "{}"'.format(db_cluster_identifier))

    blueprint = ServiceBlueprint.objects.filter(name__icontains='Cluster').first()
    group = Group.objects.first()
    resource_type = ResourceType.objects.filter(name__icontains="Database")[0]

    response = rds.describe_db_cluster_snapshots(
        DBClusterIdentifier=db_cluster_identifier,
    )
    
    for snapshot in response['DBClusterSnapshots']:
        res, created = Resource.objects.get_or_create(
            name = snapshot['DBClusterSnapshotIdentifier'],
            defaults = {
                'blueprint': blueprint,
                'group': group,
                'parent_resource': resource,
                'resource_type': resource_type,
                'lifecycle': snapshot['Status']
            }
        )

    return "SUCCESS", "", ""