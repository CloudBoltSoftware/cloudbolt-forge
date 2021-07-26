from __future__ import unicode_literals

import json
import os
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource

FILE_NAME = "{{file_name}}"
SAVE_TO = "{{save_to}}"

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


def download_object(wrapper, bucket_name: str, object_name: str, save_to_location: str):
    """
    Download an object from a bucket to a file

    Media retrieval:
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#get_media
    Downloader:
    https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.MediaIoBaseDownload-class.html
    """
    request = wrapper.objects().get_media(bucket=bucket_name, object=object_name)

    with open(save_to_location, "wb") as file:
        set_progress("Beginning to download file.")
        downloader = MediaIoBaseDownload(file, request, chunksize=1024 * 1024)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
        set_progress("Download complete!")


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


def run(job, *args, **kwargs):
    # Confirm the path is valid
    if not os.path.isdir(SAVE_TO):
        return "FAILURE", "The path to save the file isn't a valid path.", ""

    # Get system information
    save_to_location = os.path.join(SAVE_TO, FILE_NAME)
    bucket: Resource = kwargs.get("resource")
    resource_handler = GCPHandler.objects.get(id=bucket.google_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Download the object
    download_object(wrapper, bucket.name, FILE_NAME, save_to_location)

    return "SUCCESS", f"`{FILE_NAME}` Downloaded successfully to {save_to_location}", ""
