"""
Teardown service item action for Google Cloud Bigtable database.
"""

import json, tempfile
import os
import time
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

from infrastructure.models import CustomField, Environment
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler


def create_bigtable_api_wrapper(gcp_handler: GCPHandler) -> Resource:
    """
    Using googleapiclient.discovery, build the api wrapper for the bigtableadmin api:
    https://googleapis.github.io/google-api-python-client/docs/dyn/bigtableadmin_v2.projects.instances.html
    """
    credentials_dict = json.loads(gcp_handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    bigtable_wrapper: Resource = build("bigtableadmin", "v2", credentials=credentials, cache_discovery=False)
    return bigtable_wrapper


def delete_bigtable(wrapper: Resource, project_id: str, instance_id: str):
    """
    Delete a bigtable instance 
    https://cloud.google.com/bigtable/docs/reference/admin/rest/v2/projects.instances/delete
    """

    instance_str = f"projects/{project_id}/instances/{instance_id}"

    delete_request = wrapper.projects().instances().delete(name=instance_str)  

    # return should be None
    return delete_request.execute()


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    instance_id = resource.attributes.get(field__name='instance_name').value
    project_id = resource.attributes.get(field__name='project_id').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCPHandler.objects.get(id=rh_id)

    set_progress('Connecting to Google Cloud...')
    wrapper = create_bigtable_api_wrapper(rh)
    set_progress("Connection established")

    set_progress("\nDeleting instance %s..." % instance_id)
    delete_bigtable(wrapper, project_id, instance_id)
    # Will raise an informative NotFound exception if instance does not exist,
    # which will appear in CloudBolt job output.

    set_progress("Instance %s deleted" % instance_id)