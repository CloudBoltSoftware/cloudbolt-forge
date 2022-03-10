from common.methods import set_progress

from botocore.client import ClientError
from resourcehandlers.aws.models import AWSHandler

from resources.models import Resource, ResourceType
from infrastructure.models import CustomField


def generate_options_for_obj_name(server=None, **kwargs):
    resource = kwargs.get('resource', None)
    options = []

    if resource:
        aws = AWSHandler.objects.get(id=resource.aws_rh_id)

        wrapper = aws.get_api_wrapper()
        wrapper.region_name = resource.s3_bucket_region

        bucket_name = resource.s3_bucket_name

        client = wrapper.get_boto3_client(
            's3',
            aws.serviceaccount,
            aws.servicepasswd,
            wrapper.region_name
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


def get_resource_type_if_created():
    rt = ResourceType.objects.get(
        name="cloud_file_object"
    )

    cf, _ = CustomField.objects.get_or_create(
        name='cloud_file_obj_size'
    )

    if rt:
        # set_progress("Found Cloud File Object Type")
        rt.list_view_columns.add(cf)

    return rt


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    name = "{{ obj_name }}"
    bucket = resource.s3_bucket_name

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    wrapper = aws.get_api_wrapper()
    wrapper.region_name = resource.s3_bucket_region
    set_progress("This resource belongs to {}".format(aws))

    client = wrapper.get_boto3_client(
        's3',
        aws.serviceaccount,
        aws.servicepasswd,
        wrapper.region_name
    )

    try:
        res = client.get_object(
            Bucket=bucket,
            Key=name
        )
        set_progress("AWS: Found file '{}' on bucket '{}', initiating delete...".format(name, bucket))
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
    set_progress("AWS: File '{}' deleted from bucket '{}' Successfully!".format(name, bucket))

    rt = get_resource_type_if_created()
    current_object = Resource.objects.get(parent_resource=resource, resource_type=rt, name=name)

    set_progress("CloudBolt: Removing file '{}' from Cloud File Object...".format(
        current_object.name, resource.name))
    current_object.delete()

    return "SUCCESS", f"{name} has been successfuly deleted.", ""