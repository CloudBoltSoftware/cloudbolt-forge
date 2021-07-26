from __future__ import unicode_literals

import json
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource

FILE_NAME = "{{file_name}}"

# Helper functions for the discover_resources() function
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


def delete_object_in_gcp(
    wrapper: GCPResource,
    bucket_name: str,
    object_name: str,
):
    """
    Delete objects in a bucket
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#delete
    """
    request = wrapper.objects().delete(
        bucket=bucket_name,
        object=object_name,
    )
    request.execute()
    set_progress("File deleted in GCP.")


def get_blob_resource(parent_resource: Resource, name: str) -> Optional[Resource]:
    try:
        return Resource.objects.get(
            lifecycle="ACTIVE",
            resource_type__name__iexact="GCP_Blob",
            parent_resource=parent_resource,
            name=name,
        )
    except Resource.DoesNotExist:
        return None


def delete_object_in_cb(
    bucket: Resource,
    object_name: str,
):
    """
    If there's a blob resource, delete it.
    """
    blob = get_blob_resource(bucket, object_name)

    if blob:
        blob.delete()
        set_progress(f"The GCP Blob resource has been deleted in CloudBolt.")
    else:
        set_progress(f"The GCP Blob resource was not found in CloudBolt.")
        return


def generate_options_for_file_name(**kwargs):
    """
    Get all blobs/object names in the bucket.
    """
    resource: Resource = kwargs.get("resource")
    if not resource:
        return []

    objects_in_bucket = Resource.objects.filter(parent_resource=resource)
    object_names = [o.name for o in objects_in_bucket]

    return object_names


# The main function for this plugin
def run(job, *args, **kwargs):
    # Get system information
    resource: Resource = kwargs.get("resource")
    resource_handler = GCPHandler.objects.get(id=resource.google_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Delete the objects
    delete_object_in_gcp(wrapper, resource.bucket_name, FILE_NAME)
    delete_object_in_cb(resource, FILE_NAME)

    return "SUCCESS", f"`{FILE_NAME}` has been deleted", ""
