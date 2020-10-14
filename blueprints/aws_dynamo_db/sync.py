from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group

import boto3
from common.methods import set_progress

RESOURCE_IDENTIFIER = 'table_name'


def discover_resources(**kwargs):
    discovered_tables = []
    blueprint = ServiceBlueprint.objects.filter(name__iexact="Backup").first()
    dynamodb_blueprint = ServiceBlueprint.objects.filter(name__iexact="Dynamo DB").first()
    group = Group.objects.first()
    resource_type = ResourceType.objects.filter(name__iexact='Backup').first()
    dynamodb_resource_type = ResourceType.objects.filter(name__iexact='Database').first()

    for rh in AWSHandler.objects.all():
        environments = Environment.objects.filter(resource_handler=rh)

        for env in environments:
            if env.aws_region:
                dynamodb = boto3.client(
                    'dynamodb',
                    region_name=env.aws_region,
                    aws_access_key_id=rh.serviceaccount,
                    aws_secret_access_key=rh.servicepasswd,
                )
                try:
                    response = dynamodb.list_tables()
                    tables = response.get('TableNames')
                    for table in tables:
                        data = {
                            'name': table,
                            'aws_rh_id': rh.id,
                            'aws_region': env.aws_region,
                            'table_name': table,
                        }
                        # Discover backups for this table
                        response = dynamodb.list_backups(
                                TableName=table)

                        if data not in discovered_tables:
                            resource, _ = Resource.objects.get_or_create(
                                name=table,
                                blueprint=dynamodb_blueprint,
                                defaults={
                                    'group': group,
                                    'lifecycle': 'Active',
                                    'resource_type': dynamodb_resource_type})

                            resource.aws_rh_id = rh.id
                            resource.aws_region = env.aws_region
                            resource.table_name = table
                            resource.save()

                            if response:
                                backups = response['BackupSummaries']

                                for backup in backups:
                                    res, _ = Resource.objects.get_or_create(
                                        name=backup['BackupName'],
                                        blueprint=blueprint,
                                        defaults={
                                            'group': group,
                                            'parent_resource': resource,
                                            'lifecycle': 'Active',
                                            'resource_type': resource_type})

                                    res.backup_arn = backup['BackupArn']
                                    res.aws_rh_id = rh.id
                                    res.aws_region = env.aws_region
                                    res.save()

                            discovered_tables.append(data)
                except Exception as e:
                    set_progress(e)
                    continue
    return discovered_tables
