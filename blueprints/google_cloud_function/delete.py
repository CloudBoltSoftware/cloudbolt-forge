"""
Teardown service item action for Google Cloud function
"""

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from resourcehandlers.gcp.models import GCPHandler
from common.methods import set_progress
import json
from google.oauth2.credentials import Credentials

def run(resource, logger=None, **kwargs):
    rh = GCPHandler.objects.get(id=resource.google_rh_id)

    set_progress('Connecting to Google Cloud')

    credentials_dict = json.loads(rh.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)

    service_name = 'cloudfunctions'
    version = 'v1'
    client = build(service_name, version, credentials=credentials, cache_discovery=False)

    set_progress("Connection established")

    result = client.projects().locations().functions().delete(name=resource.function_name).execute()

    if result.get('name'):
        set_progress(f"{resource.name} has been deleted")
        return "SUCCESS", "", ""

    return "FAILURE", "", ""
