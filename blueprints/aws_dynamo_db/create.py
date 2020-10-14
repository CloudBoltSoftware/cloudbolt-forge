from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment

import boto3


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='table_name', defaults={
            'label': 'DynamoDB table name', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='name', defaults={
            'label': 'Name', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def run(resource, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()

    table_name = "{{ table_name }}"
    primary_key = "{{ primary_key }}"

    dynamodb = boto3.client(
        'dynamodb',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': primary_key,
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': primary_key,
                'AttributeType': 'S'
            }],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    set_progress(f"Waiting for {table_name} to be available")
    # Wait until the table exists.
    dynamodb.get_waiter('table_exists').wait(TableName=table_name)

    create_custom_fields_as_needed()

    resource.name = table_name
    resource.aws_rh_id = rh.id
    resource.aws_region = env.aws_region
    resource.table_name = table_name
    resource.save()

    return "SUCCESS", "", ""
