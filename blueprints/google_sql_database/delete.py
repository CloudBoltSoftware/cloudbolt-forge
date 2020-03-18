"""
Teardown service item action for Google Cloud SQL database.
"""
import json

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler


def run(job, logger=None, **kwargs):
    resource = kwargs.get('resource')
    try:

        instance_name = resource.attributes.get(field__name='gcp_sql_instance_name').value
        rh_id = resource.attributes.get(field__name='gcp_sql_rh_id').value
        rh = GCPHandler.objects.get(id=rh_id)

        set_progress('Connecting to Google Cloud')

        project = resource.attributes.get(field__name='gcp_sql_project').value

        try:
            account_info =  json.loads(rh.gcp_projects.get(id=project).service_account_info)
        except Exception:
            account_info = json.loads(rh.gcp_projects.get(id=project).service_account_key)

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(account_info)

        service_name = 'sqladmin'
        version = 'v1beta4'
        client = build(service_name, version, credentials=credentials)

        set_progress("Connection established")

        set_progress('Deleting instance %s...' % instance_name)

        # It takes awhile for the DB to be deleted

        result = client.instances().delete(project=project, instance=instance_name).execute()
   #     Verify that instance was deleted:
        inst_data = client.instances().list(project=project).execute()
        if 'items' in inst_data:
            for inst in inst_data['items']:
                if inst['name'] == instance_name:
                    return "WARNING", 'Server instance "%s" could not be deleted' % instance_name

        set_progress('\nInstance %s is now deleted' % instance_name)
    except Exception as e:
        return "ERROR", 'Server instance "%s" could not be deleted' % resource.name, e

