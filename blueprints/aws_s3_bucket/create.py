"""
Build service item action for AWS S3 Bucket blueprint.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
from accounts.models import Group
import boto3


def generate_options_for_env(server=None, **kwargs):
    options = []
    group_name=(kwargs['group']).name
    gp=Group.objects.get(name=group_name)
    options=[(env.id,env.name) for env in gp.environments.all() if env.resource_handler.resource_technology.type_slug.lower()=="aws"]
    if len(options)!=0:
        return sorted(options, key=lambda tup: tup[1].lower())
    else:
        raise Exception("group is not associated with any environment")

def generate_options_for_s3_region(server=None, **kwargs):
    options = []
    for region in boto3.session.Session().get_available_regions('s3'):
        label = region[:2].upper() + region[2:].title()
        options.append((region, label.replace('-', ' ')))
    return sorted(options, key=lambda tup: tup[1].lower())


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={'type': 'STR',
                  'label': 'AWS RH ID',
                  'description': 'Resource handler ID for Resource handler being used to connect to AWS'
                  })


def run(**kwargs):
    env_id = '{{ env }}'
    region = '{{ s3_region }}'
    new_bucket_name = '{{ s3_bucket_name_input }}'
    env=Environment.objects.get(id=env_id)
    rh = env.resource_handler
    wrapper = rh.get_api_wrapper()
    create_custom_fields()

    resource = kwargs.pop('resources').first()
    resource.name = new_bucket_name
    # Store bucket name and region on this resource as attributes
    resource.s3_bucket_name = new_bucket_name
    resource.s3_bucket_region = region
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.aws_rh_id = rh.id
    resource.save()

    set_progress('Connecting to Amazon S3...')
    conn = wrapper.get_boto3_resource(
        rh.serviceaccount,
        rh.servicepasswd,
        region,
        service_name='s3'
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