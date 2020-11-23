from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    wrapper = aws.get_api_wrapper()
    set_progress("This resource belongs to {}".format(aws))

    path_name = "{{ path }}"
    upload_to = "{{ name }}"

    s3 = wrapper.get_boto3_resource(
        aws.serviceaccount,
        aws.servicepasswd,
        None,
        service_name='s3'
    )
    s3.meta.client.upload_file(path_name, resource.s3_bucket_name, upload_to)

    return "SUCCESS", "The object has succesfully been copied", ""
