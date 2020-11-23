from common.methods import set_progress

from botocore.client import ClientError
from resourcehandlers.aws.models import AWSHandler


def run(job, resource, **kwargs):
    set_progress("Connecting to AWS s3 cloud")
    objects = "{{ objects }}"

    aws = AWSHandler.objects.get(id=resource.aws_rh_id)
    wrapper = aws.get_api_wrapper()
    set_progress("This resource belongs to {}".format(aws))

    s3 = wrapper.get_boto3_resource(
        aws.serviceaccount,
        aws.servicepasswd,
        None,
        service_name='s3'
    )
    not_downloaded = []
    downloads = objects.split(',')

    for name in downloads:
        try:
            res = s3.meta.client.download_file(resource.s3_bucket_name, name, f'/tmp/{name}')
            set_progress(res)
        except ClientError as e:
            set_progress(e)
            not_downloaded.append(name)
    if len(not_downloaded) > 0:
        return "WARNING", f"{not_downloaded} have not been downloaded" , ""
    return "SUCCESS", f"{downloads} have been downloaded.", ""
