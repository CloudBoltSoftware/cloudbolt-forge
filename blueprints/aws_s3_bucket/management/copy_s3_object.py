from common.methods import set_progress

from resourcehandlers.aws.models import AWSHandler


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")
    source_object = "{{ source_object }}"
    destination_bucket = "{{ destination_bucket }}"

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    wrapper = aws.get_api_wrapper()
    set_progress("This resource belongs to {}".format(aws))

    s3 = wrapper.get_boto3_resource(
        aws.serviceaccount,
        aws.servicepasswd,
        None,
        service_name='s3'
    )
    copy_source = {
        'Bucket': resource.s3_bucket_name,
        'Key': 'steve.jpg'
    }
    s3.meta.client.copy(copy_source, destination_bucket, source_object)

    return "SUCCESS", "The object has succesfully been copied", ""
