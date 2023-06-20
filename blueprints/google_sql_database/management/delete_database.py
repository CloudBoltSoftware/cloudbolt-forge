"""
Plug-in for delete a Google SQL database on an existing Instance
"""
from __future__ import unicode_literals

import json
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.gcp.models import GCPHandler, GCPProject
from utilities.exceptions import CloudBoltException

DB_NAME = "{{ database_name }}"


class GCPAdmin(object):
    """
    This Class leverages CloudBolt Environments to provide authentication to
    GCP and the Google Discovery APIs:
    https://developers.google.com/apis-explorer

    Use:
        gcp_admin = GCPAdmin(environment)
        compute_client = gcp_admin.get_client("compute")
    """

    def __init__(self, environment):
        self.environment = environment
        self.handler = environment.resource_handler.cast()
        assert isinstance(self.handler, GCPHandler)
        gcp_project = GCPProject.objects.get(id=self.environment.gcp_project)
        self.project_name = gcp_project.gcp_id
        try:
            account_info = json.loads(gcp_project.service_account_info)
        except Exception:
            account_info = json.loads(gcp_project.service_account_key)

        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            account_info)
        self.client_email = account_info["client_email"]
        set_progress(
            "Connecting to Google Cloud through service account email "
            "{}".format(self.client_email)
        )
        set_progress("RH: %s" % self.handler)
        self.storage_client = self.get_client("sqladmin", "v1beta4")

    def get_client(self, serviceName, version="v1"):
        return build(serviceName, version, credentials=self.credentials)


def generate_options_for_database_name(resource=None, **kwargs):
    options = resource.gcp_sql_instance_dbs
    if not options:
        options = []
    return options

def wait_for_operation(client, gcp_admin, operation_id):
    # Wait the server instance to be created:
    max_retries = 5
    retries = 0
    while True:
        operation_status = None
        try:
            operation_data = client.operations().get(
                project=gcp_admin.project_name,
                operation=operation_id).execute()
            operation_status = operation_data["status"]
        except HttpError as e:
            # The GCP service didn't always respond during testing, This
            # addresses failures and retries to get the operation status
            retries += 1
            if retries == max_retries:
                msg = f"Operations exceeded max retries. Error: {e}"
                set_progress(msg)
                raise Exception(msg)

        if operation_status == 'DONE':
            set_progress(f'SQL Create Operation Complete. Checking for Errors')
            try:
                error = operation_data["error"]
                if error:
                    raise CloudBoltException(f'Error in operation: {error}')
            except KeyError:
                set_progress(f'Operation is error free. exiting')
            break

        set_progress(f"Status of the operation is: {operation_status}")
        time.sleep(5)

def store_instance_db_names(gcp_admin, instance_name, resource):
    ignore_dbs = ['mysql', 'information_schema', 'performance_schema', 'sys',
                  'master', 'model', 'msdb', 'tempdb', 'postgres']
    client = gcp_admin.storage_client
    result = client.databases().list(project=gcp_admin.project_name,
                                     instance=instance_name).execute()
    instance_dbs = []
    for item in result["items"]:
        item_name = item["name"]
        try:
            ignore_dbs.index(item_name)
        except:
            instance_dbs.append(item_name)
    resource.set_value_for_custom_field('gcp_sql_instance_dbs', instance_dbs)
    resource.save()


def run(job=None, logger=None, **kwargs):
    """
    """
    db_name = DB_NAME
    resource = kwargs.get("resource")
    instance_name = resource.attributes.get(
        field__name="gcp_sql_instance_name"
    ).value
    set_progress("Connecting to Google Cloud")

    project_name = resource.attributes.get(field__name="gcp_sql_project").value
    project = GCPProject.objects.get(gcp_id=project_name)
    environment = project.environment
    gcp_admin = GCPAdmin(environment)
    client = gcp_admin.storage_client

    # Delete the Database
    set_progress(f"Attempting to delete database: {db_name}")
    result = client.databases().delete(project=gcp_admin.project_name,
                                       instance=instance_name,
                                       database=db_name).execute()
    operation_id = result["name"]
    wait_for_operation(client, gcp_admin, operation_id)

    set_progress(f"Database {db_name} has been deleted from instance:"
                 f" {instance_name}")

    store_instance_db_names(gcp_admin, instance_name, resource)