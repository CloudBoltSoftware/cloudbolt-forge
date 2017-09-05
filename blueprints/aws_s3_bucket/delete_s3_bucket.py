"""
Teardown service item action for AWS S3 Bucket blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3


def run(job, logger=None, **kwargs):
    service = job.service_set.first()

    bucket_name = service.attributes.get(field__name='s3_bucket_name').value
    rh_id = service.attributes.get(field__name='aws_rh_id').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon S3')
    conn = boto3.resource(
        's3',
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    bucket = conn.Bucket(bucket_name)

    set_progress('Deleting S3 Bucket "{}" and contents'.format(bucket_name))
    bucket.delete()

    return "", "", ""
