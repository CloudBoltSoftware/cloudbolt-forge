#!/usr/bin/env python
# This CB plugin is used by the 'LAMP CloudFormation' blueprint

import boto3
from common.methods import set_progress

from resourcehandlers.aws.models import AWSHandler
from utilities.exceptions import CloudBoltException


def run(job, logger, resources=None):
    """
    `resources` is a queryset (of length 1) of resources being acted on.
    That resource should have a 'aws_stack_name' attribute or nothing is deleted.
    """
    resource = resources.first()
    if not resource:
        raise CloudBoltException("No resource provided, this needs to be run as a pre-delete "
                                 "resource action")

    rh = AWSHandler.objects.first()
    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    session = boto3.Session(
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
        region_name='us-west-2'
    )
    client = session.client('cloudformation')

    stack_name = resource.attributes.filter(field__name="aws_stack_name").first()
    if not stack_name:
        set_progress("No aws_stack_name attribute set on resource; skipping.")
        return "FAILURE", "", ""

    stack_name = stack_name.value
    set_progress("Deleting Stack {}".format(stack_name))
    response = client.delete_stack(StackName=stack_name)
    logger.debug("Response: {}".format(response))
    return "", "", ""
