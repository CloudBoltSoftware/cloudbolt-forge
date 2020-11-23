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
    save_to = "{{ save_to }}"

    if not os.path.isdir(save_to):
        return "FAILURE", "The path to save the file isn't a valid path", ""

    client = create_client(resource_handler)
    bucket = client.get_bucket(resource.bucket_name)

    if not bucket:
        return "FAILURE", "Bucket does not exist", f"Bucket `{resource.bucket_name}` does not exist"
    blob = bucket.blob(file_name)
    if not blob.exists():
        return "FAILURE", f"`{file_name}` does not exist on this bucket", ""

    save_to_location = os.path.join(save_to, file_name)
    res = blob.download_to_filename(save_to_location)
    if not res:
        return "SUCCESS", f"`{file_name}` Downloaded successfully", ""
