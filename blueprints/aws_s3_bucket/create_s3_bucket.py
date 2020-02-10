"""
Build service item action for AWS S3 Bucket blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from resourcehandlers.aws.models import AWSHandler
import boto3


def generate_options_for_aws_rh(server=None, **kwargs):
    options = []
    for rh in AWSHandler.objects.all():
        options.append((rh.id, rh.name))
    return sorted(options, key=lambda tup: tup[1].lower())


def generate_options_for_s3_region(server=None, **kwargs):
    options = []
    for region in boto3.session.Session().get_available_regions('s3'):
        label = region[:2].upper() + region[2:].title()
        options.append((region, label.replace('-', ' ')))
    return sorted(options, key=lambda tup: tup[1].lower())


def run(job, logger=None, **kwargs):
    rh_id = '{{ aws_rh }}'
    region = '{{ s3_region }}'
    new_bucket_name = '{{ s3_bucket_name_input }}'
    rh = AWSHandler.objects.get(id=rh_id)
    CustomField.objects.get_or_create(
        name='aws_rh_id', label='AWS RH ID', type='STR',
        description='Used by the AWS S3 Bucket blueprint'
    )

    resource = kwargs.pop('resources').first()
    resource.name = 'S3 Bucket - ' + new_bucket_name
    # Store bucket name and region on this resource as attributes
    resource.s3_bucket_name = new_bucket_name
    resource.s3_bucket_region = region
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.aws_rh_id = rh.id
    resource.save()

    set_progress('Connecting to Amazon S3')
    conn = boto3.resource(
        's3',
        region_name=region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Create S3 bucket "{}"'.format(new_bucket_name))
    if region == 'us-east-1':
        conn.create_bucket(
            Bucket=new_bucket_name,
        )
    else:
        conn.create_bucket(
            Bucket=new_bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': region
            }
        )

    return "", "", ""
