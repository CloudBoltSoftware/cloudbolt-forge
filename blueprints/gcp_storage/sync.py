from __future__ import unicode_literals

import json
from typing import List, Dict, Optional, Union

from accounts.models import Group
from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource
from googleapiclient.discovery import build
from googleapiclient.http import HttpError
from infrastructure.models import CustomField
from resourcehandlers.gcp.models import GCPHandler
from resources.models import Resource, ResourceType
from servicecatalog.models import ServiceBlueprint

RESOURCE_IDENTIFIER = "bucket_name"
api_dict = Dict[str, Union[str, List, Dict]]


# Helper functions for the discover_resources() function
def create_custom_field_objects_if_missing():
    """
    Create custom fields for GCP Bucket Resources
    This is copied in both the create and sync scripts.
    """
    CustomField.objects.get_or_create(
        name="gcp_rh_id",
        defaults={
            "label": "GCP Resource Handler ID",
            "type": "STR",
            "description": "Used by the GCP Storage blueprint",
        },
    )
    CustomField.objects.get_or_create(
        name="bucket_name",
        defaults={
            "label": "Google Storage bucket name",
            "type": "STR",
            "description": "Used by the GCP Storage blueprint",
        },
    )
    CustomField.objects.get_or_create(
        name="gcp_project_id",
        defaults={
            "label": "GCP Storage bucket project id",
            "type": "STR",
            "description": "Used by the GCP Storage blueprint",
        },
    )


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
    buckets = _get_paginated_list_result(wrapper.buckets, "items", project=project_id)
    # the api returns buckets without their project_id, so we add it here
    for bucket in buckets:
        bucket["project_id"] = project_id
    return buckets


# The main function for this plugin
def discover_resources(**kwargs):
    """
    Finds all buckets in all projects in all GCP resource handlers currently imported
    into CloudBolt
    """
    discovered_google_storage = []

    # Gather system information
    gcp_storage_blueprint = ServiceBlueprint.objects.filter(
        name__iexact="GCP Storage"
    ).first()
    group = Group.objects.first()
    storage_resource_type = ResourceType.objects.filter(name__iexact="Storage").first()

    # Set up custom fields if necessary
    create_custom_field_objects_if_missing()

    # Loop through all existing GCPHandlers
    for handler in GCPHandler.objects.all():
        wrapper = create_storage_api_wrapper(handler)

        # If we can't create an API wrapper for this handler, skip it.
        if not wrapper:
            continue

        # Get the buckets
        buckets = get_buckets_in_handler(handler, wrapper)
        set_progress(f"Found {len(buckets)} buckets in {handler}")

        # Import the buckets
        for bucket in buckets:
            bucket_name = str(bucket.get("name", ""))
            project_id = str(bucket.get("project_id", ""))

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

            # Add extra information onto the Resource
            set_progress(f"Adding extra info on resource for bucket: {bucket}")
            storage_bucket.gcp_rh_id = handler.id
            storage_bucket.gcp_project_id = project_id
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

    return discovered_google_storage
