"""
Teardown service for google firewall rules.
"""

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress
import time


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    google_firewall_name = resource.attributes.get(field__name='google_firewall_name').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCEHandler.objects.get(id=rh_id)

    project = rh.project

    set_progress('Connecting to Google Cloud')

    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': rh.serviceaccount,
        'private_key': rh.servicepasswd,
        'type': 'service_account',
        'project_id': project,
        'client_id': None,
        'private_key_id': None,
    })

    client = build('compute', 'v1', credentials=credentials)
    set_progress("Connection to google cloud established")

    set_progress('Deleting firewall rule %s...' % google_firewall_name)

    #delete the firewall
    client.firewalls().delete(project=project, firewall=google_firewall_name).execute()

    return "SUCCESS", "The firewall has been deleted", ""