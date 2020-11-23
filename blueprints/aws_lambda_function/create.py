"""
Build service item action for AWS Lambda function.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
import boto3
from urllib.request import urlopen
from django.conf import settings


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options

def generate_options_for_runtime(server=None, **kwargs):
    return ['nodejs', 'nodejs4.3', 'nodejs6.10', 'nodejs8.10',
            'java8', 'python2.7', 'python3.6', 'dotnetcore1.0',
            'dotnetcore2.0', 'dotnetcore2.1', 'nodejs4.3-edge', 'go1.x'
    ]

def generate_options_for_role(control_value=None, **kwargs):
    if control_value is None:
        return []
    env = Environment.objects.get(id=control_value)
    rh = env.resource_handler.cast()
    client = boto3.client(
        'iam',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )
    response = client.list_roles()
    roles = response['Roles']
    return [(r['Arn'], r['RoleName']) for r in roles]



def run(job, logger=None, **kwargs):

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    aws_region = env.aws_region
    rh = env.resource_handler.cast()
    function_name = '{{ function_name }}'
    runtime = '{{ runtime }}'
    role_arn = '{{ role }}'
    handler = '{{ handler }}'
    zip_file = '{{ zip_file }}'

    CustomField.objects.get_or_create(
        name='aws_rh_id', type='STR',
        defaults={'label':'AWS RH ID', 'description':'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label':'AWS Region', 'description':'Used by the AWS blueprints', 'show_as_attribute':True}
    )
    CustomField.objects.get_or_create(
        name='aws_function_name', type='STR',
        defaults={'label':'AWS Lambda function name', 'description':'Used by the AWS Lambda blueprint', 'show_as_attribute':True}
    )

    set_progress('Downloading %s...' % zip_file)
    if zip_file.startswith(settings.MEDIA_URL):
        set_progress("Converting relative URL to filesystem path")
        data = zip_file.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)
    set_progress('Downloaded %i bytes.' % len(data))


    set_progress('Connecting to AWS...')
    client = boto3.client(
        'lambda',
        region_name=aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress('Creating lambda %s...' % function_name)

    response = client.create_function(
        FunctionName=function_name,
        Runtime=runtime,
        Role=role_arn,
        Handler=handler,
        Code={'ZipFile': data},
    )

    print(response)
    set_progress('Function ARN: %s' % response['FunctionArn'])
    assert response['FunctionName'] == function_name

    resource = kwargs.get('resource')
    resource.name = 'AWS Lambda - ' + function_name
    resource.aws_region = aws_region
    resource.aws_rh_id = rh.id
    resource.aws_function_name = function_name
    resource.save()

    return "", "", ""
