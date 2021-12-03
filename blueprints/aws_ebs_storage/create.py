"""
Build service item action for AWS EBS Volume blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from django.db import IntegrityError
import boto3



def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options

def generate_options_for_volume_type(server=None, **kwargs):
    return [
        ('gp2', 'General Purpose SSD'),
        ('io1', 'Provisioned IOPS SSD'),
        ('sc1', 'Cold HDD'),
        ('st1', 'Throughput Optimized HDD'),
        ('standard', 'Magnetic'),
    ]

def run(job, logger=None, **kwargs):

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    volume_type = '{{ volume_type }}'
    encrypted = bool('{{ encrypted }}')

    # Constraints: 1-16384 for gp2, 4-16384 for io1, 500-16384 for st1,
    # 500-16384 for sc1, and 1-1024 for standard.
    # This plug-in limits all values to: 1-16384.
    volume_size_gb = int('{{ volume_size_gb }}')

    CustomField.objects.get_or_create(
        name='aws_rh_id', type='INT',
        defaults={'label':'AWS RH ID', 'description':'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label':'AWS Region', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='ebs_volume_id', type='STR',
        defaults={'label':'AWS Volume ID', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='ebs_volume_size', type='INT',
        defaults={'label':'Volume Size (GB)', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='volume_encrypted', type='BOOL',
        defaults={'label':'Encrypted', 'description':'Whether this volume is encrypted or not', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='volume_state', type='STR',
        defaults={'label': 'Volume status', 'description': 'Current state of the volume.',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='instance_id', type='STR',
        defaults={'label': 'Instance attached to', 'description': 'The instance this volume is attached to',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='device_name', type='STR',
        defaults={'label': 'Device name', 'description': 'The name of the device this volume is attached to',
                  'show_as_attribute': True}
    )
    set_progress('Connecting to Amazon EC2')
    ec2 = boto3.client(
        'ec2',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Creating EBS volume...')
    volume_dict = ec2.create_volume(
        Size=volume_size_gb,
        AvailabilityZone=env.aws_availability_zone,
        VolumeType=volume_type,
        Encrypted=encrypted,
    )
    volume_id = volume_dict['VolumeId']

    resource = kwargs.pop('resources').first()
    resource.name = 'EBS Volume - ' + volume_id
    resource.ebs_volume_id = volume_id
    resource.ebs_volume_size = volume_size_gb
    resource.aws_region = env.aws_region
    resource.aws_rh_id = rh.id
    resource.volume_encrypted = encrypted

    set_progress('Waiting for volume to become available...')
    waiter = ec2.get_waiter('volume_available')
    waiter.wait(VolumeIds=[volume_id])

    resource.volume_state = "available"
    resource.instance_id = "N/A"
    resource.device_name = "N/A"
    resource.save()

    set_progress('Volume ID "{}" is now available'.format(volume_id))

    return "SUCCESS", "", ""
