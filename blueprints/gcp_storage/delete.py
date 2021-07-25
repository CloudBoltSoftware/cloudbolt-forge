"""
Teardown service item action for Google Storage bucket.
"""

from __future__ import unicode_literals

import json

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from resourcehandlers.gcp.models import GCPHandler


# Helper functions for the run() function
def create_storage_api_wrapper(gcp_handler: GCPHandler) -> GCPResource:
    """
    Using googleapiclient.discovery, build the api wrapper for the storage api:
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.html
    """
    credentials_dict = json.loads(gcp_handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    storage_wrapper: GCPResource = build(
        "storage", "v1", credentials=credentials, cache_discovery=False
    )
    return storage_wrapper


def delete_bucket(
    wrapper: GCPResource,
    bucket_name: str,
) -> dict:
    """
    Create a bucket (many other aspects can be specified - see api docs for details)
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.buckets.html#insert
    """
    buckets_resource = wrapper.buckets()
    delete_request = buckets_resource.delete(bucket=bucket_name)
    created_bucket = delete_request.execute()
    return created_bucket


# The main function for this plugin
def run(job=None, logger=None, **kwargs):
    # Get system information
    resource = kwargs.pop("resources").first()
    bucket_name = resource.attributes.get(field__name="bucket_name").value
    resource_handler_id = resource.attributes.get(field__name="google_rh_id").value
    resource_handler = GCPHandler.objects.get(id=resource_handler_id)

    # Connecte to GCP
    set_progress("Connecting to Google Cloud...")
    wrapper = create_storage_api_wrapper(resource_handler)
    set_progress("Connection established")

    # Delete the bucket
    set_progress('Deleting bucket "%s"...' % bucket_name)
    try:
        delete_bucket(wrapper, bucket_name)
    except Exception as error:
        return "FAILURE", f"{error}", ""

    set_progress('Bucket "%s" was deleted' % bucket_name)
    return "SUCCESS", "", ""
