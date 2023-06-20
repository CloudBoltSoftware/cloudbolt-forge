from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError

RESOURCE_IDENTIFIER = 'aws_stack_name'


def discover_resources(**kwargs):
    discovered_cloudformations = []

    for handler in AWSHandler.objects.all():
        wrapper = handler.get_api_wrapper()
        set_progress('Connecting to Amazon Cloudformation for \
                      handler: {}'.format(handler))
        for region in handler.current_regions():
            cloudformation = wrapper.get_boto3_client(
                'cloudformation',
                handler.serviceaccount,
                handler.servicepasswd,
                region
            )
            try:
                for stack in cloudformation.list_stacks()['StackSummaries']:
                    discovered_cloudformations.append({
                        'aws_stack_name': stack['StackName'],
                        'stack_status': stack['StackStatus'],
                        "aws_rh_id": handler.id,
                        "aws_region": region
                    })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_cloudformations
