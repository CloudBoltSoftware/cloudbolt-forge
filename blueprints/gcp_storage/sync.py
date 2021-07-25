from __future__ import unicode_literals

import json
from typing import List, Dict, Optional, Union

from accounts.models import Group
from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import HttpError
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource, ResourceType
from servicecatalog.models import ServiceBlueprint

RESOURCE_IDENTIFIER = "bucket_name"
api_dict = Dict[str, Union[str, List, Dict]]


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


def get_buckets_in_handler(handler: GCPHandler, wrapper: GCPResource) -> List[api_dict]:
    """
    Gets all buckets from imported projects on the Resource Handler.
    """
    imported_projects = handler.gcp_projects.filter(imported=True)

    buckets_in_handler = []

    for project in imported_projects:
        buckets_in_project = get_buckets_in_project(wrapper, project.id)
        buckets_in_handler.extend(buckets_in_project)

    return buckets_in_handler


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


def get_buckets_in_project(wrapper: GCPResource, project_id: str) -> List[api_dict]:
    """
    Using the storage api wrapper, get all buckets from the project.
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.buckets.html#list
    """
    return _get_paginated_list_result(wrapper.buckets, "items", project=project_id)


def get_blobs_in_bucket(wrapper: GCPHandler, bucket_name: str) -> List[api_dict]:
    """
    Using the storage api wrapper, get all objects (aka blobs) from the bucket.
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.objects.html#list
    """
    return _get_paginated_list_result(wrapper.objects, "items", bucket=bucket_name)


def discover_resources(**kwargs):
    """
    Finds all buckets in all projects in all GCP resource handlers currently imported
    into CloudBolt
    """
    discovered_google_storage = []

    # Gather system information
    blob_blueprint = ServiceBlueprint.objects.filter(name__iexact="GCP Objects").first()
    gcp_storage_blueprint = ServiceBlueprint.objects.filter(
        name__iexact="GCP Storage"
    ).first()
    group = Group.objects.first()
    blob_resource_type = ResourceType.objects.filter(name__iexact="Blob").first()
    storage_resource_type = ResourceType.objects.filter(name__iexact="Storage").first()

    # Loop through all existing GCPHandlers
    for handler in GCPHandler.objects.all():
        wrapper = create_storage_api_wrapper(handler)

        # If we can't create an API wrapper for this handler, skip it.
        if not wrapper:
            continue

        # Get the buckets
        buckets = get_buckets_in_handler(handler, wrapper)
        set_progress(f"Found {len(buckets)} buckets in {handler}")

        for bucket in buckets:
            bucket_name = str(bucket.get("name", ""))

            # See if we've found this bucket already
            for storage in discovered_google_storage:
                if storage["bucket_name"] == bucket_name:
                    # Skip it if we have
                    continue

            # Create the Resource, or get the existing one
            storage_bucket, created = Resource.objects.get_or_create(
                name=bucket_name,
                defaults={
                    "blueprint": gcp_storage_blueprint,
                    "group": group,
                    "resource_type": storage_resource_type,
                },
            )

            # Update information on the Resource
            storage_bucket.google_rh_id = handler.id
            storage_bucket.bucket_name = bucket_name
            storage_bucket.lifecycle = "ACTIVE"
            storage_bucket.save()

            # Save our changes to the return list
            discovered_google_storage.append(
                {
                    "google_rh_id": handler.id,
                    "bucket_name": bucket_name,
                    "name": bucket_name,
                }
            )

            # Discover blobs while here
            blobs = get_blobs_in_bucket(wrapper, bucket_name)
            set_progress(
                f"Found {len(blobs)} blobs in bucket {bucket_name} in {handler}"
            )

            for blob in blobs:
                Resource.objects.get_or_create(
                    name=blob["name"],
                    defaults={
                        "blueprint": blob_blueprint,
                        "group": group,
                        "parent_resource": storage_bucket,
                        "resource_type": blob_resource_type,
                        "lifecycle": "ACTIVE",
                    },
                )

    return discovered_google_storage