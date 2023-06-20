from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    set_progress("This resource belongs to {}".format(aws))
    
    wrapper = aws.get_api_wrapper()
    wrapper.region_name = resource.s3_bucket_region

    file = "{{ file }}"
    key_name = "{{ name }}"

    s3 = wrapper.get_boto3_resource(
        aws.serviceaccount,
        aws.servicepasswd,
        wrapper.region_name,
        service_name='s3'
    )
    try:
        set_progress('uploading file from "{}"'.format(file))
        s3.Bucket(resource.s3_bucket_name).upload_file(file, key_name)
    except Exception as e:
        return "FAILURE", str(e), ""

    return "SUCCESS", "The file has been successfully uploaded to '{}' bucket".format(resource.s3_bucket_name), ""
