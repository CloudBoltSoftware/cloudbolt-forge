"""
Discover google cloud functions on google cloud
"""
from common.methods import set_progress
from resourcehandlers.gce.models import GCEHandler
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build

RESOURCE_IDENTIFIER = 'function_name'


def discover_resources(**kwargs):
    discovered_functions = []

    projects = []
    regions = ['us-central1', 'us-east1',
               'asia-east2', 'asia-northeast1', 'europe-west1', 'europe-west2']

    for handler in GCEHandler.objects.all():
        set_progress('Connecting to GCE for \
                      handler: {}'.format(handler))

        project = handler.project

        if project in projects:
            continue

        credentials = ServiceAccountCredentials.from_json_keyfile_dict({
            'client_email': handler.serviceaccount,
            'private_key': handler.servicepasswd,
            'type': 'service_account',
            'project_id': project,
            'client_id': None,
            'private_key_id': None,
        })

        service_name = 'cloudfunctions'
        version = 'v1'
        client = build(service_name, version, credentials=credentials, cache_discovery=False)
        set_progress("Connection established")

        for region in regions:
            results = client.projects().locations().functions().list(
                parent=f"projects/{project}/locations/{region}").execute()

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
        projects.append(project)

    return discovered_functions
