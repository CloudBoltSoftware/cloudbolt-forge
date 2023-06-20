"""
Build service item action for AWS Glacier vault blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
import boto3


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def create_custom_fields_as_required():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS RH ID',
            "type": 'STR',
            "description": 'Used by the AWS Glacier Vault blueprint'
        }
    )
    CustomField.objects.get_or_create(
        name='aws_region',
        defaults={
            "label": 'AWS Region',
            "type": 'STR',
            "description": 'Used by the AWS Glacier Vault blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='glacier_vault_name',
        defaults={
            "label": 'Glacier Vault Name',
            "type": 'STR',
            "description": 'Used by the AWS Glacier Vault blueprint'
        }
    )


def run(job, logger=None, **kwargs):
    create_custom_fields_as_required()
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    rh = env.resource_handler.cast()
    vault_name = '{{ vault_name }}'

    resource = kwargs.pop('resources').first()
    resource.name = vault_name
    resource.glacier_vault_name = vault_name
    resource.aws_region = region
    resource.aws_rh_id = rh.id
    resource.save()

    set_progress('Connecting to Amazon AWS')

    glacier = boto3.resource(
        'glacier',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Creating Glacier vault "{}"'.format(vault_name))
    glacier.create_vault(vaultName=vault_name)

    return "", "", ""
