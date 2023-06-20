"""
Build service item action for AWS security group.
"""
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.aws.models import AWSHandler
from botocore.exceptions import ClientError
import boto3

def generate_options_for_region(**kwargs):
    regions = []
    for handler in AWSHandler.objects.all():
        for env in handler.current_regions():
            regions.append(env)
    return regions

def generate_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', type='STR',
        defaults={'label':'AWS RH ID', 'description':'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label':'AWS Region', 'description':'AWS Region', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='backup_plan_name', type='STR',
        defaults={'label':'AWS Backup Plan name', 'description':'WS Backup Plan name', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='backup_plan_id', type='STR',
        defaults={'label':'AWS Backup Plan ID', 'description':'WS Backup Plan ID', 'show_as_attribute':True}
    )

def run(job, logger=None, **kwargs):
    env = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").first()
    rh = env.resource_handler.cast()

    region = "{{ region }}"
    backup_plan_name = "{{ backup_plan_name }}"
    backup_plan_rule_name = backup_plan_name + "backup-rule"
    target_backup_vault_name = backup_plan_name + "backup-vault"

    set_progress('Connecting to Amazon Backup')
    client = boto3.client('backup',
                       region_name=region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd
                       )
    
    set_progress('Create a backup plan')
    try:
        client.create_backup_vault(
            BackupVaultName=target_backup_vault_name
        )

        response = client.create_backup_plan(
            BackupPlan={
                'BackupPlanName': backup_plan_name,
                'Rules': [{
                    "RuleName": backup_plan_rule_name, 
                    'TargetBackupVaultName': target_backup_vault_name
                }]
            })
        set_progress('Amazon backup plan created succesfully.')
    except client.exceptions.AlreadyExistsException as e:
        try:
    	    response = client.create_backup_plan(
    		    BackupPlan={
    		        'BackupPlanName': backup_plan_name,
    		        'Rules': [{
    		            "RuleName": backup_plan_rule_name,
    		            'TargetBackupVaultName': target_backup_vault_name
    		        }]
    		    })
        except ClientError as e:
            return "FAILURE", "The security group could not be created. Reason: ", e	
    except ClientError as e:
        return "FAILURE", "The security group could not be created. Reason: ", e
    
    resource = kwargs.get('resource')
    resource.name = backup_plan_name
    resource.backup_plan_id = response['BackupPlanId']
    resource.aws_region = region
    resource.aws_rh_id = rh.id
    resource.backup_plan_name = backup_plan_name
    resource.save()


    return "SUCCESS", "The Backup Plan was successfully created", ""
