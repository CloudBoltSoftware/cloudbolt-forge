from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from botocore.exceptions import ClientError
from resourcehandlers.aws.models import AWSHandler
import boto3

def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    backup_plan_id = resource.attributes.get(field__name='backup_plan_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)
    backup_plan_name=resource.name
    backup_vault_name=backup_plan_name+'backup-vault'
    set_progress("Connecting to aws backups...")
    client = boto3.client('backup',
                       region_name=region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd
                       )

    

    try:
    	set_progress("Deleting the backup plan vault...")
        client.delete_backup_vault(
    BackupVaultName=backup_vault_name)
    
    	set_progress("Deleting the backup plan...")
        client.delete_backup_plan(BackupPlanId=backup_plan_id)
    except Exception as e:
        return "FAILURE", "Backup plan could not be deleted", e

    return "SUCCESS", "The network security group has been succesfully deleted", ""
