"""
Teardown service item action for Google Cloud Bigtable database.
"""

from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress
import json, tempfile
from google.cloud import bigtable
import os


def create_client(rh):
    json_fd, json_path = tempfile.mkstemp()

    json_dict = {'client_email': rh.serviceaccount,
                 'token_uri': 'https://www.googleapis.com/oauth2/v4/token',
                 'private_key': rh.servicepasswd
                 }

    with open(json_path, 'w') as fh:
        json.dump(json_dict, fh)

    client = bigtable.client.Client.from_service_account_json(json_path,
                                                              admin=True, project=rh.project)
    os.close(json_fd)
    return client


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    instance_id = resource.attributes.get(field__name='instance_name').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCEHandler.objects.get(id=rh_id)

    set_progress('Connecting to Google Cloud...')
    client = create_client(rh)
    set_progress("Connection established")

    set_progress("\nDeleting instance %s..." % instance_id)
    instance = client.instance(instance_id)
    instance.delete()
    # Will raise an informative NotFound exception if instance does not exist,
    # which will appear in CloudBolt job output.

    set_progress("Instance %s deleted" % instance_id)