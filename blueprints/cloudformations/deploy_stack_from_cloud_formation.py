#!/usr/bin/env python
# This CB plugin is used by the 'LAMP CloudFormation' blueprint

import boto3
import time
from infrastructure.models import CustomField
from orders.models import CustomFieldValue

from resourcehandlers.aws.models import AWSHandler


def run(job, logger):
    rh = AWSHandler.objects.first()

    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    session = boto3.Session(
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
        region_name='us-west-2'
    )
    client = session.client('cloudformation')

    timestamp = str(time.time())
    timestamp, _ = timestamp.split('.')

    stack_name = "LAMP{}".format(timestamp)
    # http://boto3.readthedocs.io/en/latest/reference/services/cloudformation.html?highlight=cloudformation#CloudFormation.Client.create_stack
    response = client.create_stack(
        StackName=stack_name,
        TemplateURL='https://s3-us-west-2.amazonaws.com/cloudformation-templates-us-west-2/LAMP_Single_Instance.template',
        Parameters=[
            {'ParameterKey': 'DBName', 'ParameterValue': 'MyDatabase{}'.format(timestamp)},
            {'ParameterKey': 'DBPassword', 'ParameterValue': '{{DBPassword}}'},
            {'ParameterKey': 'DBRootPassword', 'ParameterValue': '{{DBRootPassword}}'},
            {'ParameterKey': 'DBUser', 'ParameterValue': 'cloudbolt'},
            {'ParameterKey': 'InstanceType', 'ParameterValue': 't1.micro'},
            {'ParameterKey': 'KeyName', 'ParameterValue': 'pdx-key'},
            {'ParameterKey': 'SSHLocation', 'ParameterValue': '0.0.0.0/0'},
        ],
    )
    # response looks like:
    # {'ResponseMetadata': {'HTTPStatusCode': 200,
    #                       'RequestId': '0ced74c8-1ab5-11e6-87d3-f382cbbbe402'},
    # u'StackId': 'arn:aws:cloudformation:us-west-2:548575475449:stack/NewStack81/0cf3dd10-1ab5-11e6-88a6-50a68a0e32f2'}
    logger.debug("Response: {}".format(response))
    stack_id = response['StackId']

    service = job.parent_job.service_set.first()
    cf, _ = CustomField.objects.get_or_create(name="aws_stack_name", type="STR")
    cfv, _ = CustomFieldValue.objects.get_or_create(field=cf, value=stack_name)
    service.attributes.add(cfv)
    return ("", "Stack installation initiated, the new stack has name {} and ID {}".format(
        stack_name, stack_id), "")