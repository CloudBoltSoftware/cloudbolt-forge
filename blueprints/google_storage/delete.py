"""
Teardown service item action for Google Storage bucket.
"""

from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress
import json, tempfile
from infrastructure.models import CustomField, Environment
# from google.cloud import storage
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource, build
from resourcehandlers.gcp.models import GCPHandler, GCPProject


def create_client(rh):
    json_fd, json_path = tempfile.mkstemp()

    json_dict = {'client_email': rh.serviceaccount,
                 'token_uri': 'https://www.googleapis.com/oauth2/v4/token',
                 'private_key': rh.servicepasswd
                 }

    with open(json_path, 'w') as fh:
        json.dump(json_dict, fh)

    client = storage.client.Client.from_service_account_json(json_path,
                                                              project=rh.project)
    os.close(json_fd)
    return client
    

def create_storage_api_wrapper(handler):
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
    storage_wrapper = build(
        "storage", "v1", credentials=credentials, cache_discovery=False
    )
    set_progress("Connection established")

    return storage_wrapper


def delete_bucket(wrapper, bucket_name) -> dict:
    """
    Create a bucket (many other aspects can be specified - see api docs for details)
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.buckets.html#insert
    """
    buckets_resource = wrapper.buckets()
    delete_request = buckets_resource.delete(bucket=bucket_name)
    created_bucket = delete_request.execute()
    return created_bucket


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()
    bucket_name = resource.attributes.get(field__name='bucket_name').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCPHandler.objects.get(id=rh_id)
    
    wrapper = create_storage_api_wrapper(rh)
    set_progress('Deleting bucket "%s"...' % bucket_name)
    # bucket = client.bucket(bucket_name)
    try:
        # bucket.delete()
        bucket = delete_bucket(wrapper, bucket_name)
    except Exception as error:
        return "FAILURE", f"{error}", ""
    set_progress('Bucket "%s" was deleted' % bucket_name)
    return "SUCCESS", "", ""