from __future__ import unicode_literals

import json
import os
from pathlib import Path
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource
import os
import json, tempfile
from google.cloud import storage
from resourcehandlers.gcp.models import GCPHandler

FILE_NAME = "{{file_name}}"
ACCESS_CONTROL = "{{access_control}}"

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


def update_object_metadata(
    wrapper: GCPResource, bucket_name: str, object_name: str, **kwargs
):
    """
    Update metedata on an object / blob in a bucket.
    passes all kwargs to objects().update()
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#update
    """
    wrapper.objects().update(bucket=bucket_name, object=object_name, **kwargs)


# generate_options_for_* functions are used to create option in the ui
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


def generate_options_for_access_control(**kwargs):
    return [
        ("authenticatedRead", "Authenticated Users can Read"),
        ("bucketOwnerFullControl", "Project Owner is Owner"),
        ("bucketOwnerRead", "Project Owner can Read"),
        ("private", "Only Owner has access"),
        ("projectPrivate", "Project team members can Read"),
        ("publicRead", "Public"),
    ]


# The main function for this plugin
def run(job, *args, **kwargs):
    # Get system information
    bucket: Resource = kwargs.get("resource")
    resource_handler = GCPHandler.objects.get(id=bucket.google_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Update the metadata for the blob / object
    update_object_metadata(
        wrapper, bucket.name, FILE_NAME, predefinedAcl=ACCESS_CONTROL
    )

    return (
        "SUCCESS",
        f"`{FILE_NAME}` is now set to access control `{ACCESS_CONTROL}`",
        "",
    )
