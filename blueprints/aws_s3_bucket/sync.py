"""
Discover and create S3 Bucket records with some basic identifying attributes.

As all Discovery Plug-ins must do, we define the global `RESOURCE_IDENTIFIER` variable
and return a list of dictionaries from the `discover_resources` function.
"""
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

RESOURCE_IDENTIFIER = 's3_bucket_name'


def discover_resources(**kwargs):

    discovered_buckets = []    
    for handler in AWSHandler.objects.all():
        try:
            wrapper = handler.get_api_wrapper()
        except Exception as e:
            set_progress(f"Could not get wrapper: {e}")
            continue
        set_progress('Connecting to Amazon S3 for handler: {}'.format(handler))
        conn = wrapper.get_boto3_resource(
            handler.serviceaccount,
            handler.servicepasswd,
            None,
            service_name='s3'
        )

        try:
            for bucket in conn.buckets.all():
                discovered_buckets.append({
                    "name": bucket.name,
                    "s3_bucket_name": bucket.name,
                    "aws_rh_id": handler.id,
                    "created_in_s3": str(bucket.creation_date)
                })
        except ClientError as e:
            set_progress('AWS ClientError: {}'.format(e))
            continue
            
    return discovered_buckets
