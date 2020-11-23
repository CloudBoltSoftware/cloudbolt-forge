"""
Delete an aws security group
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from botocore.exceptions import ClientError
from resourcehandlers.aws.models import AWSHandler
import boto3

def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    aws_security_group_id = resource.attributes.get(field__name='aws_security_group_id').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    region = resource.attributes.get(field__name='aws_region').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress("Connecting to aws ec2...")
    ec2_client = boto3.client('ec2',
                       region_name=region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd
                       )

    set_progress("Deleting the security group...")

    try:
        ec2_client.delete_security_group(GroupId=aws_security_group_id)
        set_progress('Security Group Deleted')
    except ClientError as e:
        return "FAILURE", "Network security group could not be deleted", e

    return "SUCCESS", "The network security group has been succesfully deleted", ""