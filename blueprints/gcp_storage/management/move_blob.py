from __future__ import unicode_literals

import json
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource
from servicecatalog.models import ServiceBlueprint

FILE_NAME = "{{file_name}}"
MOVE_TO = "{{move_to}}"


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


def get_bucket_resource(handler_id: str, bucket_name: str) -> Optional[Resource]:
    # First find Resources from the same blueprint with the right name
    gcp_storage_blueprint = ServiceBlueprint.objects.filter(
        name__iexact="GCP Storage"
    ).first()
    buckets_from_all_rh = Resource.objects.filter(
        blueprint=gcp_storage_blueprint, name=bucket_name
    )
    # Then make sure it's on the same Resource Handler
    destination_bucket_resource = next(
        (x for x in buckets_from_all_rh if x.gcp_rh_id == handler_id), None
    )
    return destination_bucket_resource


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


def duplicate_blob_with_new_parent(blob: Resource, parent_resource: Resource):
    # Technique from Django docs:
    # https://docs.djangoproject.com/en/3.2/topics/db/queries/#copying-model-instances
    blob.pk = None
    blob._state.adding = True
    blob.parent_resource = parent_resource
    blob.save()


def copy_object_in_cb(
    bucket: Resource,
    destination_bucket_name: str,
    object_name: str,
):
    """
    If there's a blob resource, duplicate it.
    """
    blob = get_blob_resource(bucket, object_name)

    if not blob:
        return

    # Get destination bucket resource
    destination_bucket = get_bucket_resource(bucket.gcp_rh_id, destination_bucket_name)
    if not destination_bucket:
        set_progress(
            "Could not duplicate resource in CloudBolt. Destination Bucket "
            f"{destination_bucket_name} does not exist with a handler id "
            f"{bucket.gcp_rh_id}."
        )
        return

    # Make sure we're not already tracking the file (in case of an overwrite)
    destination_blob = get_blob_resource(destination_bucket, object_name)
    if destination_blob:
        set_progress(
            f"The Destination GCP Blob resource already exists CloudBolt. "
            "This must be an overwrite, so we're skipping the copy in CloudBolt."
        )
        return

    # Copy the blob. Technique from django docs:
    duplicate_blob_with_new_parent(blob, destination_bucket)
    set_progress(f"The GCP Blob resource has been copied in CloudBolt.")


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


# generate_options_for_* functions are used to create option in the ui
def generate_options_for_move_to(**kwargs):
    """
    Get all buckets in the same Resource Handler as the Resource
    """
    resource: Resource = kwargs.get("resource")
    if not resource:
        return []

    resource_handler = GCPHandler.objects.get(id=resource.google_rh_id)
    storage_resources = Resource.objects.filter(resource_type__name__iexact="Storage")

    # All buckets should have the custom string field 'gcp_rh_id'
    gcp_buckets = [r for r in storage_resources if hasattr(resource, "gcp_rh_id")]

    buckets_on_resource_handler = [
        b for b in gcp_buckets if b.gcp_rh_id == str(resource_handler.id)
    ]

    return buckets_on_resource_handler


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

    set_progress("Moving an object in GCP by making a copy then deleting the original.")

    # Copy the object
    copy_object_in_gcp(wrapper, resource.bucket_name, MOVE_TO, FILE_NAME)
    copy_object_in_cb(resource, MOVE_TO, FILE_NAME)

    # Delete the original object
    delete_object_in_gcp(wrapper, resource.bucket_name, FILE_NAME)
    delete_object_in_cb(resource, FILE_NAME)

    return "SUCCESS", f"`{FILE_NAME}` has been moved to {MOVE_TO}", ""
