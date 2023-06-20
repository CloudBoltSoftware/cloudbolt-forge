"""
Build service item action for AWS MariaDB database blueprint.
"""
import time
from django.db import IntegrityError
import boto3
from botocore.exceptions import ClientError
from common.methods import set_progress
from infrastructure.models import CustomField, Environment


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def generate_options_for_instance_class(**kwargs):
    return [
        ('db.t2.micro', 'Burst Capable - db.t2.micro'),
        ('db.t2.small', 'Burst Capable - db.t2.small'),
        ('db.t2.medium', 'Burst Capable - db.t2.medium'),
        ('db.t2.large', 'Burst Capable - db.t2.large'),
        ('db.m4.large', 'Standard - db.m4.large'),
        ('db.m4.xlarge', 'Standard - db.m4.xlarge'),
        ('db.m4.2xlarge', 'Standard - db.m4.2xlarge'),
        ('db.m4.4xlarge', 'Standard - db.m4.4xlarge'),
        ('db.m4.10xlarge', 'Standard - db.m4.10xlarge'),
        ('db.r3.large', 'Memory Optimized - db.r3.large'),
        ('db.r3.xlarge', 'Memory Optimized - db.r3.xlarge'),
        ('db.r3.2xlarge', 'Memory Optimized - db.r3.2xlarge'),
        ('db.r3.4xlarge', 'Memory Optimized - db.r3.4xlarge'),
        ('db.r3.8xlarge', 'Memory Optimized - db.r3.8xlarge'),
    ]


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={'label': 'AWS MariaDB RH ID', 'type': 'STR',
                                    'description': 'Used by the AWS MariaDB blueprint'}
    )

    CustomField.objects.get_or_create(
        name='db_identifier', defaults={'label': 'AWS database identifier', 'type': 'STR',
                                        'description': 'Used by the AWS MariaDB blueprint'}
    )

    CustomField.objects.get_or_create(
        name='db_address', defaults={'label': 'AWS database adress', 'type': 'STR',
                                     'description': 'Used by the AWS MariaDB blueprint'}
    )

    CustomField.objects.get_or_create(
        name='db_port', defaults={'label': 'AWS database port', 'type': 'STR',
                                  'description': 'Used by the AWS MariaDB blueprint'}
    )


def run(job, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    rh = env.resource_handler.cast()
    db_identifier = '{{ db_identifier }}'

    create_custom_fields_as_needed()

    resource = kwargs.pop('resources').first()
    resource.name = 'RDS MariaDB - ' + db_identifier
    resource.db_identifier = db_identifier
    resource.aws_region = region
    resource.aws_rh_id = rh.id
    resource.save()

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
                       region_name=region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd
                       )

    set_progress('Create RDS MariaDB database "{}"'.format(db_identifier))

    try:
        response = rds.create_db_instance(
            DBInstanceIdentifier=db_identifier,
            MasterUsername='{{ db_master_username }}',
            MasterUserPassword='{{ master_password }}',
            Engine='mariadb',
            DBInstanceClass='{{ instance_class }}',
            AllocatedStorage=5,
        )
    except Exception as err:
        return "FAILURE", "MariaDB Database could not be created", str(err)

    # check the status of the db being created
    try:
        response = rds.describe_db_instances(
            DBInstanceIdentifier=db_identifier)

        while response['DBInstances'][0]['DBInstanceStatus'] == 'creating':
            set_progress('Database "{}" is being created'.format(
                db_identifier))
            time.sleep(10)

            response = rds.describe_db_instances(
                DBInstanceIdentifier=db_identifier)
        resource.db_address = response['DBInstances'][0]['Endpoint']['Address']
        resource.db_port = response['DBInstances'][0]['Endpoint']['Port']
        resource.lifecycle = 'ACTIVE'
        resource.save()

    except ClientError as e:
        resource.delete()
        set_progress('AWS ClientError: {}'.format(e))
        return "FAILURE", "", e
    except Exception as err:
        return "FAILURE", "Amazon MariaDB could not be created", str(err)

    return "SUCCESS", "Created MariaDB successfully", ""
