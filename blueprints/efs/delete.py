"""
Teardown service item action for AWS Elastic File System blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    file_system_id = resource.attributes.get(field__name='efs_file_system_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon EFs...')
    client = boto3.client(
        'efs',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Deleting EBS "{}" and contents'.format(file_system_id))
    response = client.delete_file_system(FileSystemId=file_system_id)

    set_progress('response: %s' % response)

    return "", "", ""