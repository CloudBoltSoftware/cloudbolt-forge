"""
Teardown service item action for AWS S3 Bucket blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    bucket_name = resource.attributes.get(field__name='s3_bucket_name').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    rh = AWSHandler.objects.get(id=rh_id)
    wrapper = rh.get_api_wrapper()

    set_progress('Connecting to Amazon S3')
    conn = wrapper.get_boto3_resource(
        rh.serviceaccount,
        rh.servicepasswd,
        None,
        service_name='s3'
    )

    bucket = conn.Bucket(bucket_name)

    set_progress('Deleting S3 Bucket "{}" and contents'.format(bucket_name))
    bucket.delete()

    return "", "", ""
