from common.methods import set_progress

from botocore.client import ClientError
from resourcehandlers.aws.models import AWSHandler


def generate_options_for_obj_name(server=None, **kwargs):
    resource = kwargs.get('resource', None)
    options = []

    if resource:
        aws = AWSHandler.objects.get(id=resource.aws_rh_id)
        wrapper = aws.get_api_wrapper()
        bucket_name = resource.s3_bucket_name
        client = wrapper.get_boto3_client(
            's3',
            aws.serviceaccount,
            aws.servicepasswd,
            None
        )
        buckets = client.list_objects(Bucket=bucket_name).get('Contents', None)
        if buckets:
            options.append(('', 'Select object to be deleted'))
            for bucket in buckets:
                # Save the objects locally
                name = bucket['Key']
                size = bucket['Size']
                options.append((name, "{} ({})".format(name, size)))
    return options


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    name = "{{ obj_name }}"
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

    try:
        res = client.get_object(
            Bucket=bucket,
            Key=name
        )
    except ClientError as e:
        res = e
        set_progress(res)
        raise

    names = [name]

    client.delete_objects(
        Bucket=bucket,
        Delete={
            'Objects': [{'Key': name} for name in names]
        }
    )

    return "SUCCESS", f"{name} has been successfuly deleted.", ""
