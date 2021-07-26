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

FILE = "{{file}}"
MAKE_BLOB_PUBLIC = bool("{{make_blob_public}}")


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


def upload_object(
    wrapper, bucket_name: str, object_name: str, file_location: str, is_public: bool
):
    """
    Upload an object from a file to a bucket

    Media insertion:
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#insert
    Uploader:
    https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.MediaIoBaseUpload-class.html
    """
    upload_kwargs = {
        "mimetype": "application/octet-stream",
        "chunksize": 1024 * 1024,
        "resumable": False,
    }

    insert_kwargs = {
        "bucket": bucket_name,
        "body": {},
        "name": object_name,
        "predefinedAcl": "publicRead" if is_public else "private",
    }

    set_progress(f"Opening file '{file_location}'")
    with open(file_location) as file:
        set_progress("Beginning to upload file.")
        media = MediaIoBaseUpload(file, **upload_kwargs)
        wrapper.objects().insert(**insert_kwargs, media_body=media).execute()

    set_progress("Upload complete!")


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


def generate_options_for_make_blob_public(**kwargs):
    return [True, False]


def run(job, *args, **kwargs):
    # Confirm the path is valid
    if not os.path.exists(FILE):
        return "FAILURE", "The path to the file isn't a valid path.", ""
    file_name = Path(FILE).name

    # Get system information
    bucket: Resource = kwargs.get("resource")
    resource_handler = GCPHandler.objects.get(id=bucket.google_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Upload the object
    upload_object(wrapper, bucket.name, file_name, FILE, MAKE_BLOB_PUBLIC)

    return f"SUCCESS", f"`{file_name}` Uploaded successfully", ""
