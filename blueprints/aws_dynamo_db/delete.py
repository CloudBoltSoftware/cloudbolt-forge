from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

import boto3


def run(resource, *args, **kwargs):
    rh = AWSHandler.objects.get(id=resource.aws_rh_id)

    dynamodb = boto3.resource(
        'dynamodb',
        region_name=resource.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    table = dynamodb.Table(resource.table_name)
    if table:
        try:
            table.delete()
        except Exception as error:
            return "FAILURE", "", f"{error}"

    return "SUCCESS", "", ""
