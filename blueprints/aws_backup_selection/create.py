"""
Build service item action for AWS security group.
"""
from django.contrib.admin.utils import flatten
import boto3
from botocore.exceptions import ClientError
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.aws.models import AWSHandler
from servicecatalog.models import ServiceBlueprint


def get_all_regions():
    regions = []
    for handler in AWSHandler.objects.all():
        for env in handler.current_regions():
            regions.append(env)
    return regions


def generate_options_for_backup_plan(**kwargs):
    backup_plan_ids = []
    env = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").first()
    rh = env.resource_handler.cast()
    for region in get_all_regions():
        client = boto3.client('backup',
                              region_name=region,
                              aws_access_key_id=rh.serviceaccount,
                              aws_secret_access_key=rh.servicepasswd)
        backup_plan_ids.append([(backup_plan_id.get('BackupPlanId') + ',' + backup_plan_id.get('BackupPlanName'),
                                 backup_plan_id.get('BackupPlanName')) for backup_plan_id in client.list_backup_plans().get('BackupPlansList')])
    return flatten(backup_plan_ids)


def generate_options_for_region(control_value=None, **kwargs):
    if control_value is None:
        return []
    region = ServiceBlueprint.objects.get(id=97).resource_set.filter(
        name=control_value.split(',')[1]).first().aws_region
    return [region]


def generate_options_for_iam_role_arn(**kwargs):
    iam_role_arns = []
    env = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").first()
    rh = env.resource_handler.cast()
    for region in get_all_regions():
        client = boto3.client('iam',
                              region_name=region,
                              aws_access_key_id=rh.serviceaccount,
                              aws_secret_access_key=rh.servicepasswd)
        iam_role_arns.append([(r.get('Arn'), r.get('RoleName'))
                              for r in client.list_roles().get('Roles')])
    return flatten(iam_role_arns)


def generate_options_for_resource_class(control_value=None, **kwargs):
    if control_value is None:
        return ['DynamoDB', 'EBS', 'EFS', 'RDS', 'Storage Gateway']
    region = ServiceBlueprint.objects.get(id=97).resource_set.filter(
        name=control_value.split(',')[1]).first().aws_region
    return [(region + ',' + 'DynamoDB', 'DynamoDB'), (region + ',' + 'EBS', 'EBS'), (region + ',' + 'EFS', 'EFS'),
            (region + ',' + 'RDS', 'RDS'), (region + ',' + 'StorageGateway', 'StorageGateway')]


def generate_options_for_resource_to_add(control_value=None, **kwargs):
    if control_value is None:
        return []
    env = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").first()
    rh = env.resource_handler.cast()
    try:
        if control_value.split(',')[1] == 'DynamoDB':
            client = boto3.client('dynamodb',
                                  region_name=control_value.split(',')[0],
                                  aws_access_key_id=rh.serviceaccount,
                                  aws_secret_access_key=rh.servicepasswd)
            x = client.list_backups().get('BackupSummaries')
            return [table.get('TableArn') for table in x]
        elif control_value.split(',')[1] == 'EBS':
            client = boto3.resource('ec2',
                                    region_name=control_value.split(',')[0],
                                    aws_access_key_id=rh.serviceaccount,
                                    aws_secret_access_key=rh.servicepasswd)
            tables = client.volumes.all()
            return [table.id for table in tables]
        elif control_value.split(',')[1] == 'EFS':
            client = boto3.client('efs',
                                  region_name=control_value.split(',')[0],
                                  aws_access_key_id=rh.serviceaccount,
                                  aws_secret_access_key=rh.servicepasswd)
            tables = client.describe_file_systems().get('FileSystems')
            return [table['FileSystemId'] for table in tables]
        elif control_value.split(',')[1] == 'RDS':
            client = boto3.client('rds',
                                  region_name=control_value.split(',')[0],
                                  aws_access_key_id=rh.serviceaccount,
                                  aws_secret_access_key=rh.servicepasswd)
            databases = client.describe_db_instances().get('DBInstances')
            return [table.get('DBInstanceArn') for table in databases]
        elif control_value.split(',')[1] == 'StorageGateway':
            client = boto3.client('storagegateway',
                                  region_name=control_value.split(',')[0],
                                  aws_access_key_id=rh.serviceaccount,
                                  aws_secret_access_key=rh.servicepasswd)
            tables = client.list_gateways().get('Gateways')
            return [table.get('DBInstanceArn') for table in tables]
    except Exception:
        return []


def generate_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', type='STR',
        defaults={'label': 'AWS RH ID',
                  'description': 'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label': 'AWS Region',
                  'description': 'AWS Region', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='backup_selection_name', type='STR',
        defaults={'label': 'AWS Backup Plan name',
                  'description': 'WS Backup Plan name', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='backup_plan_id', type='STR',
        defaults={'label': 'AWS Backup Plan ID',
                  'description': 'AWS Backup Plan ID', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='iam_role_arn', type='STR',
        defaults={'label': 'AWS IAM Role arn',
                  'description': 'AWS IAM Role arn', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='backup_selection_id', type='STR',
        defaults={'label': 'AWS Backup selection ID',
                  'description': 'AWS Backup selection ID', 'show_as_attribute': True}
    )


def run(job, logger=None, **kwargs):
    env = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").first()
    rh = env.resource_handler.cast()

    region = "{{ region }}"
    backup_plan = "{{ backup_plan }}"
    selection_name = "{{ selection_name }}"
    iam_role_arn = "{{ iam_role_arn }}"
    resource_class = "{{ resource_class }}"
    resource_to_add = "{{ resource_to_add }}"

    set_progress('Connecting to Amazon Backup')
    client = boto3.client('backup',
                          region_name=region,
                          aws_access_key_id=rh.serviceaccount,
                          aws_secret_access_key=rh.servicepasswd
                          )
    response = client.create_backup_selection(
        BackupPlanId=backup_plan.split(',')[0],
        BackupSelection={
            'SelectionName': selection_name,
            'IamRoleArn': iam_role_arn,
            'Resources': [resource_to_add],
        }
    )

    resource = kwargs.get('resource')
    resource.name = selection_name
    resource.aws_region = region
    resource.aws_rh_id = rh.id
    resource.backup_selection_name = selection_name
    resource.backup_plan_id = backup_plan
    resource.iam_role_arn = iam_role_arn
    resource.save()

    return "SUCCESS", "The Backup Plan was successfully created", ""
