#!/usr/bin/env python
# This CB plugin is used by the 'LAMP CloudFormation' blueprint

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
    wrapper = rh.get_api_wrapper()

    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    client = wrapper.get_boto3_client(
        'cloudformation',
        rh.serviceaccount,
        rh.servicepasswd,
        'us-west-2'
    )

    stack_name = resource.attributes.filter(field__name="aws_stack_name").first()
    if not stack_name:
        set_progress("No aws_stack_name attribute set on resource; skipping.")
        return "FAILURE", "", ""

    stack_name = stack_name.value
    set_progress("Deleting Stack {}".format(stack_name))
    response = client.delete_stack(StackName=stack_name)
    logger.debug("Response: {}".format(response))
    return "", "", ""
