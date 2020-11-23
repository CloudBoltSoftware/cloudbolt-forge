"""
Action creates a new RDS instance and stores its data as an attribute on the
new deployed service.
"""
import json

from infrastructure.models import CustomField, Environment
from orders.models import CustomFieldValue
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress

def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS RH ID',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='db_identifier',
        defaults={
            "label": 'AWS database identifier',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )


def run(resource, logger=None, **kwargs):
    create_custom_fields_as_needed()
    set_progress('Creating AWS RDS instance...')

    # AWS requires DB Name to have a certain format (only alphanumeric). To
    # have CB properly validate user input on this parameter, an admin should go
    # to the action's detail page, edit the 'DB Name' Action Input and set a
    # "Regex constraint" value of "^[a-zA-Z]\w+$".
    db_name = '{{ db_name }}'
    db_username = '{{ db_username }}'
    db_password = '{{ db_password }}'
    db_identifier = '{{ db_identifier }}'
    instance_class = '{{ instance_class }}'
    engine = '{{ aws_rds_engine }}'
    allocated_storage = int('{{ allocated_storage }}')
    license_model = "{{ license_model }}"

    env = Environment.objects.get(id='{{ aws_environment }}')
    set_progress('Connecting to AWS RDS in region {0}.'.format(env.aws_region))
    client = connect_to_rds(env)

    rds_settings = dict(
        DBName=db_name,
        DBInstanceIdentifier=db_identifier,
        AllocatedStorage=allocated_storage,
        DBInstanceClass=instance_class,
        Engine=engine,
        MasterUsername=db_username,
        MasterUserPassword='********',
        LicenseModel=license_model,
    )
    if not license_model:
        rds_settings.pop('LicenseModel')
    # Log with password redacted, then update dict with actual password
    set_progress('RDS settings:\n{0}'.format(rds_settings))
    rds_settings.update(dict(MasterUserPassword=db_password))

    try:
        response = client.create_db_instance(**rds_settings)
    except Exception as err:
        if 'DBInstanceAlreadyExists' in str(err):
            return "FAILURE", "Database already exists", "DB instance {} exists already".format(db_identifier)
        raise

    # It takes awhile for the DB to be created and backed up.
    waiter = client.get_waiter('db_instance_available')
    waiter.config.max_attempts = 100  # default is 40 but oracle takes more time.
    waiter.wait(DBInstanceIdentifier=db_identifier)

    
    instance = boto_instance_to_dict(response['DBInstance'])
    store_instance_data_on_service(instance, resource)
    store_aws_environment_on_service(env, resource)

    resource.db_identifier = db_identifier
    resource.name = db_identifier
    resource.save()

    set_progress('RDS instance {0} created.'.format(instance['identifier']))
    return 'SUCCESS', '', ''


def connect_to_rds(env):
    """
    Return boto connection to the RDS in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    client = wrapper.get_boto3_client(
        'rds',
        rh.serviceaccount,
        rh.servicepasswd,
        env.aws_region
    )
    return client


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


def store_instance_data_on_service(instance, resource):
    """
    Create parameter and CFV objects as needed to store the JSON-formatted
    instance data in CloudBolt. Used for ongoing management of databases and the
    RDS instance.
    """
    rds_instance_cf, _ = CustomField.objects.get_or_create(
        name='rds_instance',
        defaults={'label': 'RDS Instance', 'type': 'CODE', 'description': 'JSON-formatted data about an AWS RDS instance.'}
    )
    cfv, _ = CustomFieldValue.objects.get_or_create(
        field=rds_instance_cf, value=json.dumps(instance))
    resource.attributes.add(cfv)

    # resource.rds_intance = json.dumps({'field': rds_instance_cf, 'value': json.dumps(instance)})


def store_aws_environment_on_service(env, resource):
    """
    Create parameter and CFV objects as needed to store the chosen Environment's
    ID as an attribute on the deployed service. Used by the
    "Refresh RDS Instance Data" action.
    """
    aws_env_cf, _ = CustomField.objects.get_or_create(
        name='aws_environment',
        defaults={'label': 'AWS Environment', 'type': 'INT'}
    )
    cfv, _ = CustomFieldValue.objects.get_or_create(
        field=aws_env_cf, value=env.id)
    resource.attributes.add(cfv)
    # resource.rds_intance = json.dumps({'field': aws_env_cf, 'value': env.id})


def generate_options_for_aws_environment(profile=None, **kwargs):
    envs_this_user_can_view = Environment.objects_for_profile(profile)
    aws_handlers = AWSHandler.objects.all()
    aws_envs = envs_this_user_can_view.filter(resource_handler_id__in=aws_handlers)
    return [(env.id, env.name) for env in aws_envs]


def generate_options_for_aws_rds_engine(**kwargs):
    engines = [
        'aurora',
        'aurora-mysql',
        'aurora-postgresql',
        'mariadb',
        'MySQL',
        'postgres',
        'oracle-se2',
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


def generate_options_for_license_model(**kwargs):
    return [
        "license-included",
        "bring-your-own-license",
        "general-public-license"
    ]
