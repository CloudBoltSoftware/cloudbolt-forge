"""
Teardown service item action for AWS Lambda blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    function_name = resource.attributes.get(field__name='aws_function_name').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to AWS...')
    client = boto3.client(
        'lambda',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Deleting function "%s"' % function_name)
    client.delete_function(
        FunctionName=function_name
    )

    return "", "", ""