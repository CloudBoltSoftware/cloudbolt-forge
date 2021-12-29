"""
Teardown service for google firewall rules.
"""
import json

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from oauth2client.service_account import ServiceAccountCredentials
from resourcehandlers.gcp.models import GCPHandler
from common.methods import set_progress



def run(job, logger=None, **kwargs):
    
    resource = kwargs.get("resource")
    google_firewall_name = resource.attributes.get(field__name='google_firewall_name').value
    project_id = resource.attributes.get(field__name='google_cloud_project').value
    rh_id = resource.attributes.get(field__name='google_rh_id').value
    rh = GCPHandler.objects.get(id=rh_id)

    set_progress('Connecting to Google Cloud...')
    
    credentials_dict = json.loads(rh.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    client = build("compute", "v1", credentials=credentials, cache_discovery=False)
    
    set_progress("Connection to google cloud established")

    set_progress('Deleting firewall rule %s...' % google_firewall_name)

    #delete the firewall
    client.firewalls().delete(project=project_id, firewall=google_firewall_name).execute()

    return "SUCCESS", "The firewall has been deleted", ""