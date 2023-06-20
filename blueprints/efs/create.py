"""
Build service item action for AWS Elastic File System blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from django.db import IntegrityError
import boto3
import uuid


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services")
    return [(env.id, env.name) for env in envs]

def generate_options_for_performance_mode(server=None, **kwargs):
    return [
        ('generalPurpose', 'General Purpose'),
        ('maxIO', 'Max I/O')
    ]


def run(job, logger=None, **kwargs):

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    performance_mode = '{{ performance_mode }}'
    encrypted = bool('{{ encrypted }}')

    CustomField.objects.get_or_create(
            name='aws_rh_id',
            defaults={"label": 'AWS RH ID', "type": 'STR',
            "description":'Used by the AWS blueprints'})

    CustomField.objects.get_or_create(
            name='aws_region',
            defaults={"label": 'AWS Region ID', "type": 'STR',
            "description":'Used by the AWS blueprints'})
    CustomField.objects.get_or_create(
        name='efs_file_system_id',
        defaults= {
            "label":'AWS EFS ID', "type": 'STR',
            "description": 'Used by the AWS EFS blueprint'})

    set_progress('Connecting to Amazon EFS...')
    client = boto3.client(
        'efs',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    token = str(uuid.uuid4())

    set_progress('Creating EFS %s...' % token)
    response_dict = client.create_file_system(
        CreationToken=token,
        PerformanceMode=performance_mode,
        Encrypted=encrypted,
    )
    # NOTE: For some reason this API does not allow setting of ThroughputMode.

    file_system_id = response_dict['FileSystemId']

    resource = kwargs.pop('resources').first()
    resource.name = 'EFS - ' + file_system_id
    resource.efs_file_system_id = file_system_id
    resource.aws_region = env.aws_region
    resource.aws_rh_id = rh.id
    resource.save()

    # TODO wait for LifeCycleState to become "available"?  Usually it's
    # available right away.

    set_progress('File System "{}" is now available'.format(file_system_id))

    # TODO create mount target?

    return "SUCCESS", "", ""
