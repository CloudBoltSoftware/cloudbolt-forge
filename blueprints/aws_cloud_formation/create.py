"""
Build service item action for AWS CloudFormation blueprint
"""
from common.methods import set_progress
import json
from infrastructure.models import CustomField
from infrastructure.models import Environment


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def run(job, logger=None, **kwargs):

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    region = env.aws_region
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    template_url = '{{ template_url }}'
    stack_name = '{{ stack_name }}'

    CustomField.objects.get_or_create(
        name='aws_rh_id', type='STR',
        defaults={'label': 'AWS RH ID', 'description': 'Used by the AWS blueprints'}
    )
    CustomField.objects.get_or_create(
        name='aws_region', type='STR',
        defaults={'label': 'AWS Region', 'description': 'Used by the AWS blueprints', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='aws_stack_name', type='STR',
        defaults={'label': 'AWS CloudFormation stack name', 'description': 'Used by the AWS CloudFormation blueprint', 'show_as_attribute': True}
    )

    set_progress('Connecting to AWS...')
    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    client = wrapper.get_boto3_client(
        'cloudformation',
        rh.serviceaccount,
        rh.servicepasswd,
        region
    )

    # Example parameters value:
    """[
        {"ParameterKey": "DBName", "ParameterValue": "database1"}, 
        {"ParameterKey": "DBPassword", "ParameterValue": "database1password"}, 
        {"ParameterKey": "DBRootPassword", "ParameterValue": "dpassword123"},
        {"ParameterKey": "DBUser", "ParameterValue": "dbusername"},
        {"ParameterKey": "InstanceType", "ParameterValue": "t1.micro"},
        {"ParameterKey": "KeyName", "ParameterValue": "pdx-key"},
        {"ParameterKey": "SSHLocation", "ParameterValue": "0.0.0.0/0"}
    ]"""

    json_str = '''{{ parameters }}'''  # parameters can span multiple lines
    try:
        params_dict = json.loads(json_str)
    except json.decoder.JSONDecodeError as err:
        return "FAILURE", "Failed to decode the parameters JSON", str(err)

    # http://boto3.readthedocs.io/en/latest/reference/services/cloudformation.html?highlight=cloudformation#CloudFormation.Client.create_stack
    response = client.create_stack(
        StackName=stack_name,
        TemplateURL=template_url,
        Parameters=params_dict,
    )

    # response looks like:
    # {'ResponseMetadata': {'HTTPStatusCode': 200,
    #                       'RequestId': '0ced74c8-1ab5-11e6-87d3-f382cbbbe402'},
    # u'StackId': 'arn:aws:cloudformation:us-west-2:548575475449:stack/NewStack81/0cf3dd10-1ab5-11e6-88a6-50a68a0e32f2'}
    logger.debug("Response: {}".format(response))
    stack_id = response['StackId']

    resource = kwargs.get('resource')
    resource.aws_rh_id = rh.id
    resource.aws_region = region
    resource.aws_stack_name = stack_name
    resource.save()

    return ("", "Stack installation initiated, the new stack has name {} and ID {}".format(
            stack_name, stack_id), "")
