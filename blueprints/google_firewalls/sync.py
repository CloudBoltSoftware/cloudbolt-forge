"""
Discover google cloud firewall rules
"""
from common.methods import set_progress
from resourcehandlers.gce.models import GCEHandler
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


RESOURCE_IDENTIFIER = 'google_firewall_name'


def discover_resources(**kwargs):
    discovered_firewall_rules = []

    projects = {rh.project for rh in GCEHandler.objects.all()}

    for handler in GCEHandler.objects.all():
        set_progress('Connecting to GCE for handler: {}'.format(handler))

        project = handler.project

        if project not in projects:
            continue
        credentials = ServiceAccountCredentials.from_json_keyfile_dict({
            'client_email': handler.serviceaccount,
            'private_key': handler.servicepasswd,
            'type': 'service_account',
            'project_id': project,
            'client_id': None,
            'private_key_id': None,
        })

        client = build('compute', 'v1', credentials=credentials)
        set_progress("Connection to google cloud established")

        rules = client.firewalls().list(project=project).execute()

        if rules["items"]:
            for rule in rules['items']:
                discovered_firewall_rules.append(
                    {
                        'google_rh_id': handler.id,
                        'name': rule['name'],
                        'google_firewall_name': rule['name'],
                        "google_firewall_priority": rule['priority'],
                        "google_firewall_direction": rule['direction'],
                        "google_cloud_project": project
                    }
                )
        projects.discard(project)

    return discovered_firewall_rules
