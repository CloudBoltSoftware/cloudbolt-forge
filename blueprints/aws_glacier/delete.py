"""
Teardown service item action for AWS Glacier vault blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    vault_name = resource.attributes.get(field__name='glacier_vault_name').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon AWS')
    glacier = boto3.resource(
        'glacier',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    bucket = glacier.Vault('-', vault_name)

    set_progress('Deleting AWS Glacier valut "{}" and contents'.format(vault_name))
    bucket.delete()

    return "", "", ""
