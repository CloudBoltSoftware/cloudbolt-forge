"""
Teardown service item action for Google Storage bucket.
"""

from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress
import json, tempfile
from google.cloud import storage
import os


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


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    bucket_name = resource.attributes.get(field__name='bucket_name').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCEHandler.objects.get(id=rh_id)

    set_progress('Connecting to Google Cloud...')
    client = create_client(rh)
    set_progress("Connection established")

    set_progress('Deleting bucket "%s"...' % bucket_name)
    bucket = client.bucket(bucket_name)
    try:
        bucket.delete()
    except Exception as error:
        return "FAILURE", f"{error}", ""
    set_progress('Bucket "%s" was deleted' % bucket_name)
    return "SUCCESS", "", ""
