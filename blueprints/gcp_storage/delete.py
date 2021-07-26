"""
Teardown service item action for Google Storage bucket.
"""

from __future__ import unicode_literals

import json
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from resourcehandlers.gcp.models import GCPHandler


# Helper functions for the run() function
def create_storage_api_wrapper(handler: GCPHandler) -> Optional[GCPResource]:
    """
    Using googleapiclient.discovery, build the api wrapper for the storage api.
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.html
    """
    if not handler.gcp_api_credentials:
        set_progress(f"Handler {handler} is missing gcp api credentials.")
        return None

    credentials_dict = json.loads(handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)

    set_progress(f"Connecting to GCP for handler: {handler}")
    storage_wrapper: GCPResource = build(
        "storage", "v1", credentials=credentials, cache_discovery=False
    )
    set_progress("Connection established")

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
    resource_handler_id = resource.attributes.get(field__name="gcp_rh_id").value
    resource_handler = GCPHandler.objects.get(id=resource_handler_id)

    # Connecte to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Delete the bucket
    set_progress(f'Deleting bucket "{bucket_name}"...')
    try:
        delete_bucket(wrapper, bucket_name)
        return "SUCCESS", f'Bucket "{bucket_name}" was deleted', ""
    except Exception as error:
        return "FAILURE", f"{error}", ""
