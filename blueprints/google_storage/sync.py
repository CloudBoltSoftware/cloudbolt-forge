from common.methods import set_progress
from resourcehandlers.gce.models import GCEHandler
from google.cloud import storage

from servicecatalog.models import ServiceBlueprint
from resources.models import Resource, ResourceType
from accounts.models import Group

import json, tempfile
import os

RESOURCE_IDENTIFIER = 'bucket_name'


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


def discover_resources(**kwargs):
    discovered_google_storage = []

    blob_blueprint = ServiceBlueprint.objects.filter(name__iexact="Blobs").first()
    storage_blueprint = ServiceBlueprint.objects.filter(name__iexact="Google Storage").first()
    group = Group.objects.first()
    blob_resource_type = ResourceType.objects.filter(name__iexact="Blob").first()
    storage_resource_type = ResourceType.objects.filter(name__iexact="Storage").first()

    for handler in GCEHandler.objects.all():
        set_progress('Connecting to GCE for \
                      handler: {}'.format(handler))

        client = create_client(handler)
        set_progress("Connection established")

        buckets = client.list_buckets()

        for bucket in buckets:
            exist = False
            for storage in discovered_google_storage:
                if storage['bucket_name'] == bucket.name:
                    exist = True
                    continue
            storage_bucket, created = Resource.objects.get_or_create(
                name=bucket.name,
                defaults={
                    'blueprint': storage_blueprint,
                    'group': group,
                    'resource_type': storage_resource_type})

            if exist:
                # Discover blobs while here
                blobs = bucket.list_blobs()

                for blob in blobs:
                    Resource.objects.get_or_create(
                        name=blob.name,
                        defaults={
                            'blueprint': blob_blueprint,
                            'group': group,
                            'parent_resource': storage_bucket,
                            'resource_type': blob_resource_type})
                continue
            discovered_google_storage.append(
                {
                    "google_rh_id": handler.id,
                    "bucket_name": bucket.name,
                    'name': bucket.name,
                }
            )
            storage_bucket.google_rh_id = handler.id
            storage_bucket.bucket_name = bucket.name
            storage_bucket.lifecycle = 'ACTIVE'
            storage_bucket.save()

            # Discover blobs while here
            blobs = bucket.list_blobs()

            for blob in blobs:
                Resource.objects.get_or_create(
                    name=blob.name,
                    defaults={
                        'blueprint': blob_blueprint,
                        'group': group,
                        'parent_resource': storage_bucket,
                        'resource_type': blob_resource_type,
                        'lifecycle': 'ACTIVE'
                    })

    return discovered_google_storage
