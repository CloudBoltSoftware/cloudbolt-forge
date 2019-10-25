"""
Recurring job to fetch and store the IAM Policies for all configured AWS
Resource Handlers. We write the list of policies to the filesystem as
we don't have db modeling to support AWS Policies at the time of development.

Done as part of the 9.0.1 Gartner release.
"""
import json
import os

from cbhooks.hookmodules.content_library.cache_content import write_list_to_file
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

from .iam_policy_utilities import IAM_POLICY_CACHE_LOCATION_PATH


def run(job, *args, **kwargs):

    handlers = AWSHandler.objects.all()
    for handler in handlers:
        set_progress("Fetching IAM Policies for {}".format(handler.name))
        wrapper = handler.get_api_wrapper()
        iam_client = wrapper.get_boto3_client('iam', handler.serviceaccount, handler.servicepasswd, None)

        response = iam_client.list_policies()

        exportable_policies = []
        for policy in response['Policies']:
            exportable_policies.append(
                {
                    "arn": policy['Arn'],
                    "path": policy['Path'],
                    "name": policy['PolicyName'],
                }
            )

        os.makedirs(IAM_POLICY_CACHE_LOCATION_PATH, exist_ok=True)
        path = os.path.join(IAM_POLICY_CACHE_LOCATION_PATH, 'handler-{}-policies.json'.format(handler.id))
        write_list_to_file(exportable_policies, path)
        set_progress("Collected {} IAM Policies for {}.".format(len(exportable_policies), handler.name))
