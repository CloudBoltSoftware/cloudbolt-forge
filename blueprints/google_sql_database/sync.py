"""
Discover Mysql records with some identifying attributes on GCE
return a list of dictionaries from the 'discover_resoures' function
"""
import json
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build


RESOURCE_IDENTIFIER = 'instance_name'


def discover_resources(**kwargs):
    resource = kwargs.get('resource')
    project_name = resource.attributes.get(field__name='gcp_sql_project').value
    rh_id = resource.attributes.get(field__name='gcp_sql_rh_id').value
    server_instance_name = resource.attributes.get(field__name='gcp_sql_instance_name').value   
    resource_handler = GCPHandler.objects.get(id=rh_id)
    project = resource_handler.gcp_projects.get(id=project_name)

    discovered_mysqldb = []

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(project.service_account_info))

    job.set_progress('Connecting to Google Cloud through service account email {}'.format(project.service_account_info["client_email"]))
    set_progress("RH: %s" % resource_handler)

    service_name = 'sqladmin'
    version = 'v1beta4'
    client = build(service_name, version, credentials=credentials)

    instances = client.instances().list(project=project).execute().get('items', None)

    if instances:
        for instance in instances:
            if instance['name'] == server_instance_name:
                discovered_mysqldb.append(
                    {
                        'google_rh_id': handler.id,
                        'name': instance['name'],
                        'instance_name': instance['name']
                        'resource_handler': resource_handler
                    }
                )
    return discovered_mysqldb
