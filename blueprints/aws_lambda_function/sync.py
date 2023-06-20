from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import Environment
import boto3


RESOURCE_IDENTIFIER = 'aws_function_name'

def discover_resources(**kwargs):
    lambda_functions = []
    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon Lambda for handler: {}'.format(handler))
        for env in handler.current_regions():
            set_progress('Connecting to Amazon Lmabda for handler: {}'.format(handler))
            conn = boto3.client('lambda',
                region_name=env,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd
            )
            try:
                for lambda_function in conn.list_functions()['Functions']:
                    lambda_functions.append({
                            "aws_region": env,
                            "aws_rh_id": handler.id,
                            "aws_function_name": lambda_function['FunctionName']
                            })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return lambda_functions