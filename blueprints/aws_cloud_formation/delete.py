"""
Teardown service item action for AWS CloudFormation stack.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    rh = AWSHandler.objects.get(id=rh_id)
    wrapper = rh.get_api_wrapper()
    region = resource.attributes.get(field__name='aws_region').value
    stack_name = resource.attributes.get(field__name="aws_stack_name").value

    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    client = wrapper.get_boto3_client(
        'cloudformation',
        rh.serviceaccount,
        rh.servicepasswd,
        region
    )

    set_progress('Deleting CloudFormation stack "%s"' % stack_name)
    response = client.delete_stack(StackName=stack_name)
    logger.debug("Response: {}".format(response))
    return "", "", ""
