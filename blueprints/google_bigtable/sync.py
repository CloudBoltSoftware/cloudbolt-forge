from resourcehandlers.gce.models import GCEHandler
from common.methods import set_progress
import json, tempfile
from google.cloud import bigtable
import os


RESOURCE_IDENTIFIER = 'instance_name'


def discover_resources(**kwargs):
    discovered_google_bigtable = []
    
    #create a set of all projects
    projects = {rh.project for rh in GCEHandler.objects.all()}

    for handler in GCEHandler.objects.all():
        set_progress('Connecting to Google BigTable for \
                      handler: {}'.format(handler))
        
        #only get bigtables of projects in the set
        project = handler.project
        if project not in projects:
            continue

        client = create_client(handler)
        set_progress("Connection to GCE established")
        for bigtables in client.list_instances():
            if len(bigtables) > 0:
                for bigtable in bigtables:
                    discovered_google_bigtable.append(
                        {
                            'name': bigtable.display_name,
                            'instance_name': bigtable.display_name,
                            'google_rh_id': handler.id,
                        }
                    )
        
        #remove project from the set after getting its bigtables
        projects.discard(project)
    return discovered_google_bigtable


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