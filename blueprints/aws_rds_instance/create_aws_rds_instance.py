"""
Action creates a new RDS instance and stores its data as an attribute on the
new deployed service.
"""
import json
import boto3

from infrastructure.models import CustomField, Environment
from orders.models import CustomFieldValue
from resourcehandlers.aws.models import AWSHandler


def run(job, logger=None, **kwargs):
    job.set_progress('Creating AWS RDS instance...')

    # AWS requires DB Name to have a certain format (only alphanumeric). To
    # have CB properly validate user input on this parameter, an admin should go
    # to the action's detail page, edit the 'DB Name' Action Input and set a
    # "Regex constraint" value of "^[a-zA-Z]\w+$".
    db_name = '{{ db_name }}'
    db_username = '{{ db_username }}'
    db_password = '{{ db_password }}'
    identifier = '{{ identifier }}'
    instance_class = '{{ instance_class }}'
    engine = '{{ aws_rds_engine }}'
    allocated_storage = int('{{ allocated_storage }}')
    env = Environment.objects.get(id='{{ aws_environment }}')
    job.set_progress('Connecting to AWS RDS in region {0}.'.format(env.aws_region))
    client = connect_to_rds(env)

    rds_settings = dict(
        DBName=db_name,
        DBInstanceIdentifier=identifier,
        AllocatedStorage=allocated_storage,
        DBInstanceClass=instance_class,
        Engine=engine,
        MasterUsername=db_username,
        MasterUserPassword='********',
    )
    # Log with password redacted, then update dict with actual password
    job.set_progress('RDS settings:\n{0}'.format(rds_settings))
    rds_settings.update(dict(MasterUserPassword=db_password))
    response = client.create_db_instance(**rds_settings)

    service = job.service_set.first()
    instance = boto_instance_to_dict(response['DBInstance'])
    store_instance_data_on_service(instance, service)
    store_aws_environment_on_service(env, service)

    job.set_progress('RDS instance {0} created.'.format(instance['identifier']))
    return 'SUCCESS', '', ''


def connect_to_rds(env):
    """
    Return boto connection to the RDS in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    return boto3.client(
        'rds',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd)


def boto_instance_to_dict(boto_instance):
    """
    Create a pared-down representation of an RDS instance from the full boto
    dictionary.
    """
    instance = {
        'identifier': boto_instance['DBInstanceIdentifier'],
        'engine': boto_instance['Engine'],
        'status': boto_instance['DBInstanceStatus'],
        'username': boto_instance['MasterUsername'],
    }
    # Endpoint may not be returned if networking is not set up yet
    endpoint = boto_instance.get('Endpoint', {})
    instance.update({
        'address': endpoint.get('Address'),
        'port': endpoint.get('Port')
    })
    return instance


def store_instance_data_on_service(instance, service):
    """
    Create parameter and CFV objects as needed to store the JSON-formatted
    instance data in CloudBolt. Used for ongoing management of databases and the
    RDS instance.
    """
    rds_instance_cf, _ = CustomField.objects.get_or_create(
        name='rds_instance',
        label='RDS Instance',
        type='CODE',
        description='JSON-formatted data about an AWS RDS instance.',
    )
    cfv, _ = CustomFieldValue.objects.get_or_create(
        field=rds_instance_cf, value=json.dumps(instance))
    service.attributes.add(cfv)


def store_aws_environment_on_service(env, service):
    """
    Create parameter and CFV objects as needed to store the chosen Environment's
    ID as an attribute on the deployed service. Used by the
    "Refresh RDS Instance Data" action.
    """
    aws_env_cf, _ = CustomField.objects.get_or_create(
        name='aws_environment',
        label='AWS Environment',
        type='INT',
    )
    cfv, _ = CustomFieldValue.objects.get_or_create(
        field=aws_env_cf, value=env.id)
    service.attributes.add(cfv)


def generate_options_for_aws_environment(profile=None, **kwargs):
    envs_this_user_can_view = Environment.objects_for_profile(profile)
    aws_handlers = AWSHandler.objects.all()
    aws_envs = envs_this_user_can_view.filter(resource_handler_id__in=aws_handlers)
    return [(env.id, env.name) for env in aws_envs]


def generate_options_for_aws_rds_engine(**kwargs):
    engines = [
        'MySQL',
        'postgres',
        'oracle-se1',
        'oracle-se',
        'oracle-ee',
        'sqlserver-ee',
        'sqlserver-se',
        'sqlserver-ex',
        'sqlserver-web',
    ]
    return list(zip(engines, engines))


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
