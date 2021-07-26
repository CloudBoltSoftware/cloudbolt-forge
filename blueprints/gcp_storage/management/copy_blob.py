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

FILE_NAME = "{{file_name}}"
COPY_TO = "{{copy_to}}"
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


def copy_object_in_gcp(
    wrapper: GCPResource,
    source_bucket_name: str,
    destination_bucket_name: str,
    object_name: str,
):
    """
    Copy objects from one bucket to another
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#copy
    """
    request = wrapper.objects().copy(
        sourceBucket=source_bucket_name,
        sourceObject=object_name,
        destinationBucket=destination_bucket_name,
        destinationObject=object_name,
        body={},
    )
    request.execute()
    set_progress("File copied in GCP.")


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


def generate_options_for_copy_to(**kwargs):
    """
    Get all buckets in the same Resource Handler as the Resource
    """
    resource: Resource = kwargs.get("resource")
    if not resource:
        return []

    resource_handler = GCPHandler.objects.get(id=resource.gcp_rh_id)
    storage_resources = Resource.objects.filter(resource_type__name__iexact="Storage")

    # All buckets should have the custom string field 'gcp_rh_id'
    gcp_buckets = [r for r in storage_resources if hasattr(resource, "gcp_rh_id")]

    buckets_on_resource_handler = [
        b for b in gcp_buckets if b.gcp_rh_id == str(resource_handler.id)
    ]

    return buckets_on_resource_handler


# The main function for this plugin
def run(job, *args, **kwargs):
    # Get system information
    resource: Resource = kwargs.get("resource")
    resource_handler = GCPHandler.objects.get(id=resource.gcp_rh_id)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Copy the objects
    try:
        copy_object_in_gcp(wrapper, resource.bucket_name, COPY_TO, FILE_NAME)
        return "SUCCESS", f"`{FILE_NAME}` has been copied to {COPY_TO}", ""
    except Exception as error:
        return "FAILURE", f"{error}", ""
