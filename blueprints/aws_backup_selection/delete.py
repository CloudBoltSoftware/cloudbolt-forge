from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3
import time


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    selection_name = resource.attributes.get(
        field__name='selection_name').value

    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    backup_plan_id = resource.attributes.get(
        field__name='backup_plan_id').value
    selection_id = resource.attributes.get(
        field__name='backup_selection_id').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon backup service')
    client = boto3.client('backup',
                          region_name=region,
                          aws_access_key_id=rh.serviceaccount,
                          aws_secret_access_key=rh.servicepasswd
                          )

    set_progress('Deleting AWS Backup selection "{}"'.format(selection_name))

    response = client.delete_backup_selection(
        BackupPlanId=backup_plan_id,
        SelectionId=selection_id,
    )

    while True:
        try:
            response = client.get_backup_selection(
                BackupPlanId=backup_plan_id,
                SelectionId=selection_id,
            )
        except client.exceptions.ResourceNotFoundException:
            set_progress('Backup selection succesfully deleted')
            break

    return "SUCCESS", "Backup selection succesfully deleted", ""
