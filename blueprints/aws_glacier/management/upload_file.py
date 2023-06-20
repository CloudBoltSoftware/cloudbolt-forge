from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from resourcehandler.aws.models import AWSHandler
import boto3
from django.conf import settings
from pathlib import Path


def run(job, resource, **kwargs):
	set_progress("Connecting to Amazon AWS Glacier")
	archive = '{{ archive }}'
	vault_name = '{{ vault_name }}'

	rh = AWSHandler.objects.get(id=resource.aws_rh_id)
	glacier = boto3.resource(
	    'glacier',
	    region_name=resource.aws_region,
	    aws_access_key_id=rh.serviceaccount,
	    aws_secret_access_key=rh.servicepasswd,
	)

	response = glacier.meta.client.upload_archive(vaultName=vault_name,body=archive)

	return "SUCCESS", "Upload completed successfully", ""
