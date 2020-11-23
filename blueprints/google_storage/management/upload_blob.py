from common.methods import set_progress
import os
import json, tempfile
from google.cloud import storage
from resourcehandlers.gce.models import GCEHandler
from django.conf import settings
from pathlib import Path


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


def generate_options_for_file_name(control_value=None, **kwargs):
    names = []
    if control_value:
        path = os.path.expanduser(control_value)
        names.extend([x for x in os.listdir(path)])
    return names


def generate_options_for_make_blob_public(**kwargs):
    return [True, False]


def run(job, *args, **kwargs):
	resource = kwargs.get('resource')
	resource_handler = GCEHandler.objects.get(id=resource.google_rh_id)

	file = "{{ file }}"
	file_name = Path(file).name
	make_blob_public = "{{ make_blob_public }}"
	client = create_client(resource_handler)
	bucket = client.get_bucket(resource.bucket_name)

	set_progress(bucket)
	if bucket:
	    blob = bucket.blob(file_name)
	    res = blob.upload_from_filename(name)
	    if not res:
	        if make_blob_public:
	            blob.make_public()
	        return f"SUCCESS", f"`{file_name}` Uploaded successfully", ""
	else:
	    return "FAILURE", "Bucket does not exist", f"Bucket `{resource.bucket_name}` does not exist"
