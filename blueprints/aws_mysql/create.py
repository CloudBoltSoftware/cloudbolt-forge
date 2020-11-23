"""
Build service item action for AWS MySQL database blueprint.
test2
"""
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


def run(job, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    db_identifier = '{{ db_identifier }}'

    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS MySQL RH ID',
            "type": 'STR',
            "description": 'Used by the AWS MySQL blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='db_identifier',
        defaults={
            "label": 'AWS database identifier',
            "type": 'STR',
            "description": 'Used by the AWS MySQL blueprint'
        }
    )

    resource = kwargs.pop('resources').first()
    resource.name = 'RDS MySQL - ' + db_identifier
    # Store DB identifier and region on this resource as attributes
    resource.db_identifier = db_identifier
    resource.aws_region = region
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.aws_rh_id = rh.id
    resource.save()

    set_progress('Connecting to Amazon RDS')
    rds = wrapper.get_boto3_client(
        'rds',
        rh.serviceaccount,
        rh.servicepasswd,
        region
    )

    set_progress('Create RDS MySQL database "{}"'.format(db_identifier))

    try:
        rds.create_db_instance(
            DBInstanceIdentifier=db_identifier,
            MasterUsername='{{ db_master_username }}',
            MasterUserPassword='{{ master_password }}',
            Engine='mysql',
            DBInstanceClass='{{ instance_class }}',
            AllocatedStorage=5,
        )
    except Exception as err:
        if 'DBInstanceAlreadyExists' in str(err):
            return ("FAILURE", "Database already exists", "DB instance %s exists already" % db_identifier)
        raise

    # It takes awhile for the DB to be created and backed up.
    waiter = rds.get_waiter('db_instance_available')
    waiter.wait(DBInstanceIdentifier=db_identifier)

    return "", "", ""
