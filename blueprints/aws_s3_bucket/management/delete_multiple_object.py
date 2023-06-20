from common.methods import set_progress

from botocore.client import ClientError
from resourcehandlers.aws.models import AWSHandler


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    objects = "{{ objs }}"
    bucket = resource.s3_bucket_name

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    set_progress("This resource belongs to {}".format(aws))

    wrapper = aws.get_api_wrapper()
    wrapper.region_name = resource.s3_bucket_region

    client = wrapper.get_boto3_client(
        's3',
        aws.serviceaccount,
        aws.servicepasswd,
        wrapper.region_name
    )
    names = objects.split(',')

    names_not_found = []
    for name in names:
        try:
            res = client.get_object(
                Bucket=bucket,
                Key=name
            )
        except ClientError as e:
            res = e
            names_not_found.append(name)
            set_progress(res)
            continue

    client.delete_objects(
        Bucket=bucket,
        Delete={
            'Objects': [{'Key': name} for name in names]
        }
    )

    if len(names_not_found) > 0:
        return "WARNING", f"{names_not_found} names were not found.", ""
    return "SUCCESS", f"{names} have been successfully deleted.", ""
