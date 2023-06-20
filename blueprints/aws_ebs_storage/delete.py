"""
Teardown service item action for AWS EBS Volume blueprint.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    volume_id = resource.attributes.get(field__name='ebs_volume_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon S3')
    ec2 = boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Creating EBS volume...')

    set_progress('Deleting EBS Volume "{}" and contents'.format(volume_id))
    response = ec2.delete_volume(VolumeId=volume_id)
    set_progress('response: %s' % response)

    return "", "", ""
