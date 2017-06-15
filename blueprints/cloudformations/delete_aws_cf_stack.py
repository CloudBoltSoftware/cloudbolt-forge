#!/usr/bin/env python
# This CB plugin is used by the 'LAMP CloudFormation' blueprint

import boto3
from common.methods import set_progress

from resourcehandlers.aws.models import AWSHandler
from utilities.exceptions import CloudBoltException


def run(job, logger, service=None):
    if not service:
        raise CloudBoltException("No service provided, this needs to be run as a pre-delete "
                                 "service action")

    rh = AWSHandler.objects.first()
    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    session = boto3.Session(
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
        region_name='us-west-2'
    )
    client = session.client('cloudformation')

    stack_name = service.attributes.filter(field__name="aws_stack_name").first()
    if not stack_name:
        return "", "", ""
    stack_name = stack_name.value
    set_progress("Deleting Stack {}".format(stack_name))
    response = client.delete_stack(StackName=stack_name)
    logger.debug("Response: {}".format(response))
    return "", "", ""

