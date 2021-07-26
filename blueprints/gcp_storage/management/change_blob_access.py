from __future__ import unicode_literals

import json
from typing import Dict, List, Optional, Union

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import HttpError
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

FILE_NAME = "{{file_name}}"
ACCESS_CONTROL = "{{access_control}}"
api_dict = Dict[str, Union[str, List, Dict]]

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
    wrapper.objects().update(bucket=bucket_name, object=object_name, body={}, **kwargs)


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


# generate_options_for_* functions are used to create option in the ui
def generate_options_for_file_name(**kwargs):
    """
    Get all blobs/object names in the bucket.
    """
    bucket: Resource = kwargs.get("resource")
    if not bucket:
        return []

    # Gather system info
    handler_id = bucket.google_rh_id
    bucket_name = bucket.name

    # Connect to Google
    handler = GCPHandler.objects.get(id=handler_id)
    wrapper = create_storage_api_wrapper(handler)

    # Get Blob / Object names
    blobs = get_blobs_in_bucket(wrapper, bucket_name)
    object_names = [blob["name"] for blob in blobs]

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

    # Check if we can change the public / private settings
    if bucket_has_uniform_level_access(wrapper, bucket.name):
        message = (
            f"Bucket {bucket.name} has uniform bucket level access set. Can not "
            "change privacy setting for an individual blob / object. Read why at "
            "https://cloud.google.com/storage/docs/uniform-bucket-level-access"
        )
        return "FAILURE", message, ""

    # Update the metadata for the blob / object
    try:
        update_object_metadata(
            wrapper, bucket.name, FILE_NAME, predefinedAcl=ACCESS_CONTROL
        )
        return (
            "SUCCESS",
            f"`{FILE_NAME}` is now set to access control `{ACCESS_CONTROL}`",
            "",
        )
    except Exception as error:
        return "FAILURE", f"{error}", ""
