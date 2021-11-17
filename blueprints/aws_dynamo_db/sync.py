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
        
        # Retrieving unique list of active/imported regions for 'rh' resource handler
        imported_region_list = list(rh.current_regions())
        
        for region in imported_region_list:
            if region:
                dynamodb = boto3.client(
                    'dynamodb',
                    region_name=region,
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
                            'aws_region': region,
                            'table_name': table,
                        }
                        # Discover backups for this table
                        response = dynamodb.list_backups(
                                TableName=table)

                        if data not in discovered_tables:
                            discovered_tables.append(data)
                            
                except Exception as e:
                    set_progress(e)
                    continue

    return discovered_tables
