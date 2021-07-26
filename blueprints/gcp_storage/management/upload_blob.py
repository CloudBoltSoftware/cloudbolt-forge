from __future__ import unicode_literals

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import HttpError, MediaIoBaseUpload
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

FILE = "{{file}}"
MAKE_BLOB_PUBLIC = bool("{{make_blob_public}}")
api_dict = Dict[str, Union[str, List, Dict]]


# Helper functions for the main function below
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


def bucket_has_uniform_level_access(wrapper: GCPResource, bucket_name: str) -> bool:
    """
    If a bucket is set to control access to blobs, we can't specify the individual
    blob's public vs private setting.
    """
    bucket = wrapper.buckets().get(bucket=bucket_name).execute()
    logger.info(f"Got info for bucket: {bucket}")
    iam_configuration = bucket.get("iamConfiguration", {})
    access_configuration = iam_configuration.get("uniformBucketLevelAccess", {})
    has_uniform_level_access = access_configuration.get("enabled", False)
    return has_uniform_level_access


def upload_object(
    wrapper: GCPResource,
    bucket_name: str,
    object_name: str,
    file_location: str,
    make_public: bool,
):
    """
    Upload an object from a file to a bucket
    If a bucket isn't

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
    }

    if bucket_has_uniform_level_access(wrapper, bucket_name):
        set_progress(
            f"Bucket {bucket_name} has uniform bucket level access set. Ignoring "
            "privacy selection for the 'Make Blob Public' option. Read why at "
            "https://cloud.google.com/storage/docs/uniform-bucket-level-access"
        )
    else:
        insert_kwargs["predefinedAcl"] = ("publicRead" if make_public else "private",)

    set_progress(f"Opening file '{file_location}'")
    with open(file_location, "rb") as file:
        set_progress("Beginning to upload file.")
        media = MediaIoBaseUpload(file, **upload_kwargs)
        wrapper.objects().insert(**insert_kwargs, media_body=media).execute()

    set_progress("Upload complete!")


def _get_paginated_list_result(
    resource_method, collection_name: str, *args, **kwargs
) -> List[api_dict]:
    """
    Call a method on a collection on a resource that returns a paginated list.
    *args and **kwargs get passed to the list collection
    Returns an un-paginated list and handles HttpErrors.

    For example, calling for the list of images you'd call:
        _get_paginated_list_result(
            self.compute.images, 'items', project=project_id
        )
    This gets self.compute.images().list(project=project_id)['items'], then appends
    further pages using self.compute.images().list_next()
    """
    request = resource_method().list(*args, **kwargs)
    collection = []

    while request is not None:
        try:
            response = request.execute()
            collection_page = response.get(collection_name, [])
            collection.extend(collection_page)

            request = resource_method().list_next(
                previous_request=request, previous_response=response
            )

        except HttpError as er:
            set_progress(f"There was an error while executing a Google API call: {er}")
            break

    return collection


def get_blobs_in_bucket(wrapper: GCPHandler, bucket_name: str) -> List[api_dict]:
    """
    Using the storage api wrapper, get all objects (aka blobs) from the bucket.
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#list
    """
    return _get_paginated_list_result(wrapper.objects, "items", bucket=bucket_name)


# generate_options_for_* functions are used to create option in the ui
def generate_options_for_file_name(**kwargs):
    """
    Get all blobs/object names in the bucket.
    """
    bucket: Resource = kwargs.get("resource")
    if not bucket:
        return []

    # Gather system info
    handler_id = bucket.gcp_rh_id
    bucket_name = bucket.name

    # Connect to Google
    handler = GCPHandler.objects.get(id=handler_id)
    wrapper = create_storage_api_wrapper(handler)

    # Get Blob / Object names
    blobs = get_blobs_in_bucket(wrapper, bucket_name)
    object_names = [blob["name"] for blob in blobs]

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
    resource_handler = GCPHandler.objects.get(id=bucket.gcp_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Upload the object
    try:
        upload_object(wrapper, bucket.name, file_name, FILE, MAKE_BLOB_PUBLIC)
        return f"SUCCESS", f"`{file_name}` Uploaded successfully", ""
    except Exception as error:
        return "FAILURE", f"{error}", ""
