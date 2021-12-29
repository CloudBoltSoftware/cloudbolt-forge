"""
Discover google cloud firewall rules
"""
from common.methods import set_progress
from infrastructure.models import Environment
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from resourcehandlers.gcp.models import GCPHandler
import json

RESOURCE_IDENTIFIER = 'google_firewall_name'


def discover_resources(**kwargs):
    discovered_firewall_rules = []

    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    projects = {env.gcp_project for env in gcp_envs}

    for handler in GCPHandler.objects.all():
        set_progress('Connecting to GCP handler: {}'.format(handler))
        
        #only get firewall of projects in the set
        for env in Environment.objects.filter(resource_handler_id=handler.id):
            project_id = env.gcp_project
            if project_id not in projects:
                continue
            
            credentials_dict = json.loads(handler.gcp_api_credentials)
            credentials = Credentials(**credentials_dict)
            client = build("compute", "v1", credentials=credentials, cache_discovery=False)
            
            set_progress("Connection to google cloud established")
            
            gcp_project = handler.gcp_projects.get(id = project_id).gcp_id
            
            rules = client.firewalls().list(project=gcp_project).execute()
    
            if rules["items"]:
                for rule in rules['items']:
                    discovered_firewall_rules.append(
                        {
                            'google_rh_id': handler.id,
                            'name': rule['name'],
                            'google_firewall_name': rule['name'],
                            "google_firewall_priority": rule['priority'],
                            "google_firewall_direction": rule['direction'],
                            "google_cloud_project": gcp_project
                        }
                    )
        projects.discard(gcp_project)
    
    return discovered_firewall_rules