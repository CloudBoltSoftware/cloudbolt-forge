"""
Teardown service item action for Google Cloud function
"""

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress


def run(resource, logger=None, **kwargs):
    rh = GCEHandler.objects.get(id=resource.google_rh_id)

    set_progress('Connecting to Google Cloud')

    project = rh.project

    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': rh.serviceaccount,
        'private_key': rh.servicepasswd,
        'type': 'service_account',
        'project_id': project,
        'client_id': None,
        'private_key_id': None,
    })

    service_name = 'cloudfunctions'
    version = 'v1'
    client = build(service_name, version, credentials=credentials, cache_discovery=False)

    set_progress("Connection established")

    result = client.projects().locations().functions().delete(name=resource.function_name).execute()

    if result.get('name'):
        set_progress(f"{resource.name} has been deleted")
        return "SUCCESS", "", ""

    return "FAILURE", "", ""

