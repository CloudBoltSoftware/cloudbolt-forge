"""
Take backup for AWS Dynamo DB.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group
from infrastructure.models import CustomField

import boto3


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='backup_arn', defaults={
            'label': 'Dynamo Db Backup ARN', 'type': 'STR',
            'show_as_attribute': True,
            'description': 'Used while deleting a backup'
        }
    )


def run(resource, **kwargs):
    create_custom_fields_as_needed()

    region = resource.aws_region
    rh_id = resource.aws_rh_id
    table_name = resource.table_name
    backup_name = "{{ backup_name }}"

    handler = AWSHandler.objects.get(id=rh_id)
    blueprint = ServiceBlueprint.objects.filter(name__iexact="Backup").first()
    group = Group.objects.first()
    resource_type = ResourceType.objects.filter(name__iexact='Backup').first()

    set_progress('Connecting to Amazon Dynamodb')

    dynamodb = boto3.client('dynamodb',
                            region_name=region,
                            aws_access_key_id=handler.serviceaccount,
                            aws_secret_access_key=handler.servicepasswd
                            )

    set_progress('Creating backup for "{}"'.format(table_name))

    try:
        response = dynamodb.create_backup(
            TableName=table_name,
            BackupName=backup_name)

    except Exception as error:
        return "FAILURE", "", f"{error}"

    set_progress(f'Backup Response {response}')
    if response:
        backup_details = response['BackupDetails']
        backup_arn = backup_details['BackupArn']

        res, _ = Resource.objects.get_or_create(
            name=backup_name,
            blueprint=blueprint,
            defaults={
                'group': group,
                'resource_type': resource_type})

        res.backup_arn = backup_arn
        res.parent_resource = resource
        res.lifecycle = 'Active'
        res.aws_rh_id = rh_id
        res.aws_region = region
        res.save()

    return "SUCCESS", "Backup has successfully been created", ""
