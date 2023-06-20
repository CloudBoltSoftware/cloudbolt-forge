from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.exceptions import ClientError
import boto3


def run(resource, *args, **kwargs):
    rh = AWSHandler.objects.get(id=resource.aws_rh_id)

    client = boto3.client(
        'cloudformation',
        region_name=resource.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    
    try:
        _=client.delete_stack(name=resource.name)
    except ClientError as error:
        return "FAILURE", "", f"{error}"

    return "SUCCESS", "", ""
