"""
Teardown service item action for AWS S3 Bucket blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(**kwargs):
    resource = kwargs.pop('resources').first()

    bucket_name = resource.s3_bucket_name
    rh_id = resource.aws_rh_id
    rh = AWSHandler.objects.get(id=rh_id)
    wrapper = rh.get_api_wrapper()

    set_progress('Connecting to Amazon S3...')
    conn = wrapper.get_boto3_resource(
        rh.serviceaccount,
        rh.servicepasswd,
        None,
        service_name='s3'
    )

    bucket = conn.Bucket(bucket_name)

    set_progress(f'Deleting S3 Bucket "{bucket_name}" and contents...')
    response = bucket.delete()

    response_status = response.get('ResponseMetadata').get('HTTPStatusCode')
    if response_status != 204:
        return "FAILURE", f"Error while deleting {bucket_name}", f"{response}"

    return "SUCCESS", "Bucket Deleted successfully", ""
