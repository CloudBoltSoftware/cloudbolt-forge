"""
Create a db cluster in AWS.
"""
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from botocore.client import ClientError
import boto3
import time

def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options

def generate_options_for_engine(server=None, **kwargs):
    options = ['aurora', 'aurora-mysql', 'aurora-postgresql']
    return options

def run(job, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    vpc_id = env.vpc_id
    handler = env.resource_handler.cast()

    db_cluster_identifier = '{{ db_cluster_identifier }}'
    master_username = "{{ master_username }}"
    master_password = "{{ master_password }}"

    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults = {'label': 'AWS DB Cluster RH ID', 'type': 'STR',
        'description': 'Used by the AWS DB Cluster blueprint'}
    )

    CustomField.objects.get_or_create(
        name='db_cluster_identifier', defaults = {'label': 'AWS database cluster identifier', 'type': 'STR',
        'description': 'Used by the AWS DB Cluster blueprint'}
    )

    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label':'AWS Region', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )

    resource = kwargs.pop('resources').first()
    resource.name = 'RDS DB Cluster - ' + db_cluster_identifier
    resource.db_cluster_identifier = db_cluster_identifier
    resource.aws_region = region
    resource.aws_rh_id = handler.id
    resource.save()

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
        region_name=region,
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )

    set_progress('Creating cluster "{}"'.format(db_cluster_identifier))
    try:
        rds.create_db_cluster(
            BackupRetentionPeriod=1,
            DBClusterIdentifier=db_cluster_identifier,
            Engine="{{ engine }}",
            MasterUsername=master_username,
            MasterUserPassword=master_password
        )
    except ClientError as e:
        set_progress('AWS ClientError: {}'.format(e))

    return "SUCCESS", "Cluster has succesfully been created", ""
