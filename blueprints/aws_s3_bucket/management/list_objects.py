from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def get_all_objects(client, bucket_name):
    discovered_objects = []
    buckets = client.list_objects(Bucket=bucket_name).get('Contents', None)
    if buckets:
        for bucket in buckets:
            # Save the objects locally
            discovered_objects.append(
                {
                    bucket_name: {
                        "name": bucket['Key'],
                        "size": bucket['Size']
                    }
                })
    return discovered_objects


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    bucket = resource.s3_bucket_name

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    wrapper = aws.get_api_wrapper()
    set_progress("This resource belongs to {}".format(aws))

    client = wrapper.get_boto3_client(
        's3',
        aws.serviceaccount,
        aws.servicepasswd,
        None
    )
    res = get_all_objects(client, bucket)
    set_progress(res)

    return "SUCCESS", "", ""
