import os
import json, tempfile
from google.cloud import storage
from resourcehandlers.gce.models import GCEHandler


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


def generate_options_for_copy_to(**kwargs):
    all_buckets = []
    resource = kwargs.get('resource')
    if resource:
        resource_handler = GCEHandler.objects.get(id=resource.google_rh_id)
        client = create_client(resource_handler)
        buckets = client.list_buckets()
        all_buckets.extend([bucket.name for bucket in buckets if bucket.name != resource.bucket_name])
    return all_buckets


def generate_options_for_file_name(**kwargs):
    all_files = []
    resource = kwargs.get('resource')
    if resource:
        resource_handler = GCEHandler.objects.get(id=resource.google_rh_id)
        client = create_client(resource_handler)
        bucket = client.get_bucket(resource.bucket_name)
        blobs = bucket.list_blobs()
        all_files.extend([blob.name for blob in blobs])

    return all_files


def run(job, *args, **kwargs):
    resource = kwargs.get('resource')
    resource_handler = GCEHandler.objects.get(id=resource.google_rh_id)

    file_name = "{{file_name}}"
    copy_to = "{{copy_to}}"

    client = create_client(resource_handler)
    source_bucket = client.get_bucket(resource.bucket_name)
    destination_bucket = client.get_bucket(copy_to)

    if not destination_bucket.exists():
        return "FAILURE", "Bucket does not exist", f"Bucket `{copy_to}` does not exist"
    if not source_bucket:
        return "FAILURE", "Bucket does not exist", f"Bucket `{resource.bucket_name}` does not exist"

    source_blob = source_bucket.blob(file_name)

    if not source_blob.exists():
        return "FAILURE", f"`{file_name}` does not exist on this bucket", ""

    res = source_bucket.copy_blob(
        source_blob, destination_bucket, file_name)

    if res:
        return "SUCCESS", f"`{file_name}` has been copied to {copy_to}", ""
