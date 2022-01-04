"""
Plug-in for creating a Google Storage bucket.
"""
from __future__ import unicode_literals
from infrastructure.models import CustomField, Environment
from common.methods import set_progress
import json, tempfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource as GCPResource, build
from resourcehandlers.gcp.models import GCPHandler, GCPProject
import os


def generate_options_for_env_id(server=None, **kwargs):
    gce_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    options = []
    for env in gce_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError("No valid Google Compute Engine resource handlers in CloudBolt")
    return options


def generate_options_for_storage_type(server=None, **kwargs):
    return [
        ('MULTI_REGIONAL', 'Multi-Regional'),
        ('REGIONAL', 'Regional'),
        ('NEARLINE', 'Nearline'),
        ('COLDLINE', 'Coldline'),
        # "STANDARD"
        # "DURABLE_REDUCED_AVAILABILITY"
    ]


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


def create_bucket(wrapper, project_id, bucket_name, storage_type):
    """
    Create a bucket (many other aspects can be specified - see api docs for details)
    https://googleapis.github.io/google-api-python-client/docs/dyn/storage_v1.buckets.html#insert
    """
    body = {"name": bucket_name, "storageClass": storage_type}
    buckets_resource = wrapper.buckets()
    insert_request = buckets_resource.insert(project=project_id, body=body)
    created_bucket = insert_request.execute()
    return created_bucket


def run(job=None, logger=None, **kwargs):
    storage_type = '{{ storage_type }}'
    bucket_name = '{{ bucket_name }}'

    environment = Environment.objects.get(id='{{ env_id }}')
    gcp_project = GCPProject.objects.get(id=environment.gcp_project)
    project_id = gcp_project.gcp_id
    rh = environment.resource_handler.cast()
    location_id = str(environment.node_location)
    set_progress("RH: %s" % rh)
    set_progress('location_id: %s' % location_id)

    CustomField.objects.get_or_create(
        name='google_rh_id',
        defaults={
            "label": 'Google RH ID', "type": 'STR',
            "description": 'Used by the Google storage blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='bucket_name',
        defaults={
            "label": 'Google Storage bucket name',
            "type": 'STR',
            "description": 'Used by the Google Cloud storage blueprint'
        }
    )

    resource = kwargs.pop('resources').first()
    resource.name = bucket_name
    resource.bucket_name = bucket_name
    resource.google_rh_id = rh.id
    resource.save()
    
    wrapper = create_storage_api_wrapper(rh)
    
    set_progress("Storage type: %s" % storage_type)

    set_progress('Creating Google storage bucket: "%s" of type %s' % (bucket_name, storage_type))
    bucket = create_bucket(wrapper, project_id, bucket_name, storage_type)
    # bucket.storage_class = storage_type
    set_progress('Created storage bucket: "%s"' % bucket_name)

    return "SUCCESS", "", ""