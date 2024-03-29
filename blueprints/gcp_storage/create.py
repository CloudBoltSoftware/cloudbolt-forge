"""
Plug-in for creating a Google Storage bucket.
"""
from __future__ import unicode_literals

import json
from logging import error
from typing import Optional

from common.methods import set_progress
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource, build
from infrastructure.models import CustomField, Environment
from resources.models import Resource
from resourcehandlers.gcp.models import GCPHandler, GCPProject

# Get templated information
STORAGE_TYPE = "{{ storage_type }}"
BUCKET_NAME = "{{ bucket_name }}"
ENVIRONMENT_ID = "{{ env_id }}"


# generate_options_for_* functions are used to create option in the ui
def generate_options_for_env_id(server=None, **kwargs):
    gcp_environments = Environment.objects.filter(
        resource_handler__resource_technology__slug="gcp"
    )
    options = [(env.id, env.name) for env in gcp_environments]
    if not options:
        raise RuntimeError(
            "No valid Environments on Google Compute Platform resource handlers in CloudBolt"
        )
    return options


def generate_options_for_storage_type(server=None, **kwargs):
    return [
        ("MULTI_REGIONAL", "Multi-Regional"),
        ("REGIONAL", "Regional"),
        ("NEARLINE", "Nearline"),
        ("COLDLINE", "Coldline"),
        ("ARCHIVE", "Archive"),
        ("STANDARD", "Standard"),
        ("DURABLE_REDUCED_AVAILABILITY", "Durable Reduced Availability"),
    ]


# Helper functions for the run() function
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


def update_resource(
    resource: Resource, bucket_name: str, project_id: str, resource_handler: GCPHandler
):
    resource.name = bucket_name
    resource.bucket_name = bucket_name
    resource.gcp_project_id = project_id
    resource.gcp_rh_id = resource_handler.id
    resource.save()


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


def create_bucket(
    wrapper: GCPResource, project_id: str, bucket_name: str, storage_type: str
) -> dict:
    """
    Create a bucket (many other aspects can be specified - see api docs for details)
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.buckets.html#insert
    """
    body = {"name": bucket_name, "storageClass": storage_type}
    buckets_resource = wrapper.buckets()
    insert_request = buckets_resource.insert(project=project_id, body=body)
    created_bucket = insert_request.execute()
    return created_bucket


# The main function for this plugin
def run(job=None, logger=None, **kwargs):
    # Get system information
    environment = Environment.objects.get(id=ENVIRONMENT_ID)
    gcp_project = GCPProject.objects.get(id=environment.gcp_project)
    project_id = gcp_project.gcp_id
    # project_id = environment.GCP_project
    resource_handler = environment.resource_handler.cast()

    set_progress(f"Resource Handler: {resource_handler}")
    set_progress(f"Storage type: {STORAGE_TYPE}")

    # Set up the Resource
    create_custom_field_objects_if_missing()
    resource = kwargs.pop("resources").first()
    update_resource(resource, BUCKET_NAME, project_id, resource_handler)

    # Connect to GCP
    wrapper = create_storage_api_wrapper(resource_handler)
    if not wrapper:
        error_message = "Please verify the connection on the Resource Handler."
        return "FAILURE", "", error_message

    # Create the bucket
    set_progress(
        f'Creating Google storage bucket: "{BUCKET_NAME}" of type {STORAGE_TYPE}'
    )
    try:
        bucket = create_bucket(wrapper, project_id, BUCKET_NAME, STORAGE_TYPE)
        return "SUCCESS", f'Created storage bucket: "{bucket}"', ""
    except Exception as error:
        return "FAILURE", f"{error}", ""
