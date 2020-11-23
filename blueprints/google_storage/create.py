"""
Plug-in for creating a Google Storage bucket.
"""
from __future__ import unicode_literals
from infrastructure.models import CustomField, Environment
from common.methods import set_progress
import json, tempfile
from google.cloud import storage
import os


def generate_options_for_env_id(server=None, **kwargs):
    gce_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Compute Engine")
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


def run(job=None, logger=None, **kwargs):
    storage_type = '{{ storage_type }}'
    bucket_name = '{{ bucket_name }}'

    environment = Environment.objects.get(id='{{ env_id }}')
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

    set_progress("Storage type: %s" % storage_type)

    job.set_progress('Connecting to Google Cloud...')
    client = create_client(rh)
    set_progress("Connection established")

    set_progress('Creating Google storage bucket: "%s" of type %s' % (bucket_name, storage_type))
    bucket = client.create_bucket(bucket_name)
    bucket.storage_class = storage_type
    set_progress('Created storage bucket: "%s"' % bucket_name)

    return "SUCCESS", "", ""
