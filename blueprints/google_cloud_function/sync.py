"""
Discover google cloud functions on google cloud
"""
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import json

RESOURCE_IDENTIFIER = 'function_name'


def discover_resources(**kwargs):
    discovered_functions = []

    projects = []
    for handler in GCPHandler.objects.all():
        set_progress('Connecting to GCP for \
                      handler: {}'.format(handler))

        projects = handler.gcp_projects.get(imported=True)

       
        for project in projects:
            project_name=project.name
            credentials_dict = json.loads(handler.gcp_api_credentials)
            credentials = Credentials(**credentials_dict)
            
    
            service_name = 'cloudfunctions'
            version = 'v1'
            client = build(service_name, version, credentials=credentials, cache_discovery=False)
            locations=client.projects().locations().list(name=f'projects/{project_name}').execute()
            regions= [region.get('locationId') for region in locations['locations']]
            set_progress("Connection established")
    
            for region in regions:
                results = client.projects().locations().functions().list(
                    parent=f"projects/{project_name}/locations/{region}").execute()
    
                functions = results.get('functions')
                if functions:
                    for result in functions:
                        print(result)
                        discovered_functions.append(
                            {
                                'name': result.get('name').split('/')[-1],
                                'google_rh_id': handler.id,
                                'function_name': result.get('name'),
                                'available_memory_mb': result.get('availableMemoryMb'),
                                'entry_point': result.get('entryPoint'),
                                'runtime': result.get('runtime'),
                                'service_account_email': handler.serviceaccount,
                                'https_trigger': result.get('httpsTrigger').get('url'),
                                'source_archive_url': result.get('sourceArchiveUrl'),
                            }
                        )

    return discovered_functions
