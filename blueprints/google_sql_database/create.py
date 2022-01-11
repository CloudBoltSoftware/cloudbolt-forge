"""
Plug-in for creating a Google SQL database. This will create a Database
Instance and then create a database on the instance
"""
from __future__ import unicode_literals

import json
import time

from django.db import IntegrityError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.gcp.models import GCPHandler, GCPProject
from utilities.exceptions import CloudBoltException

ENVIRONMENT = "{{ env_id }}"
INSTANCE_NAME = "{{ instance_name }}"
DB_NAME = "{{ database_name }}"
DB_VERSION = "{{ db_version }}"
GCP_REGION = "{{ gcp_region }}"
TIER = "{{ tier }}"
ROOT_PASSWORD = "{{ root_password }}"

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
        return build(serviceName, version, credentials=self.credentials, cache_discovery=False)


def generate_options_for_gcp_region(control_value=None,**kwargs):
    if control_value is None:
        return []
    environment = Environment.objects.get(id=control_value)
    gcp_admin = GCPAdmin(environment)
    
    client = build('compute', 'v1', credentials=gcp_admin.credentials, cache_discovery=False)
    response = client.regions().list(project=gcp_admin.project_name).execute()
    return [(item['name'], item['name']) for item in response['items']]


def generate_options_for_env_id(server=None, **kwargs):
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform"
    )
    options = []
    for env in gcp_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError(
            "No valid Google Cloud Platform resource handlers in CloudBolt"
        )
    return options


def generate_options_for_db_version(server=None, **kwargs):
    return [
        ("MYSQL_5_7", "My SQL 5.7"),
        ("MYSQL_5_6", "My SQL 5.6"),
        ("MYSQL_8_0", "My SQL 8.0"),
        ("POSTGRES_9_6", "PostgreSQL 9.6"),
        ("POSTGRES_11", "PostgreSQL 11"),
        ("POSTGRES_13", "PostgreSQL 13"),
        ("SQLSERVER_2017_STANDARD", "SQL Server 2017 Standard"),
        ("SQLSERVER_2017_ENTERPRISE", "SQL Server 2017 Enterprise"),
        ("SQLSERVER_2017_EXPRESS", "SQL Server 2017 Express"),
        ("SQLSERVER_2017_WEB", "SQL Server 2017 Web"),
    ]


def generate_options_for_tier(control_value=None, **kwargs):
    if control_value is None:
        return []
    if control_value.find('MYSQL') == 0:
        tier_options = [
            ("db-f1-micro", "db-f1-micro"),
            ("db-g1-small", "db-g1-small"),
            ("db-n1-standard-1", "db-n1-standard-1"),
            ("db-n1-standard-2", "db-n1-standard-2"),
            ("db-n1-standard-4", "db-n1-standard-4"),
            ("db-n1-standard-8", "db-n1-standard-8"),
            ("db-n1-standard-16", "db-n1-standard-16"),
            ("db-n1-standard-32", "db-n1-standard-32"),
            ("db-n1-standard-64", "db-n1-standard-64"),
            ("db-n1-standard-96", "db-n1-standard-96"),
            ("db-n1-highmem-1", "db-n1-highmem-1"),
            ("db-n1-highmem-2", "db-n1-highmem-2"),
            ("db-n1-highmem-4", "db-n1-highmem-4"),
            ("db-n1-highmem-8", "db-n1-highmem-8"),
            ("db-n1-highmem-16", "db-n1-highmem-16"),
            ("db-n1-highmem-32", "db-n1-highmem-32"),
            ("db-n1-highmem-64", "db-n1-highmem-64"),
            ("db-n1-highmem-96", "db-n1-highmem-96"),
        ]
    else:
        # Postgres and SQL Server Tiers must be custom. You can add any sizes
        # here needed as long as RAM is greater than 3.75 GB
        tier_options = [
            ("db-custom-1-4096", " 1 CPU 4 GB RAM"),
            ("db-custom-2-4096", " 2 CPU 4 GB RAM"),
            ("db-custom-4-8192", " 4 CPU 8 GB RAM"),
            ("db-custom-8-16384", " 8 CPU 16 GB RAM"),
            ("db-custom-16-32768", "16 CPU 32 GB RAM"),
        ]

    return tier_options


def create_custom_fields():
    try:
        CustomField.objects.get_or_create(
            name="gcp_sql_rh_id",
            label="Google RH ID",
            type="STR",
            description="Used by the Google SQL blueprint",
            show_as_attribute=True,
        )
    except IntegrityError:
        # IntegrityError: (1062, "Duplicate entry 'google_rh_id' for key 'name'")
        pass

    try:
        CustomField.objects.get_or_create(
            name="gcp_sql_instance_name",
            label="Google instance identifier",
            type="STR",
            description="Used by the Google Cloud SQL blueprint",
            show_as_attribute=True,
        )
    except IntegrityError:
        # IntegrityError: (1062, "Duplicate entry 'db_identifier' for key 'name'")
        pass

    try:
        CustomField.objects.get_or_create(
            name="gcp_sql_project",
            label="Google project",
            type="STR",
            description="Used by the Google Cloud SQL blueprint",
            show_as_attribute=True,
        )
    except IntegrityError:
        # IntegrityError: (1062, "Duplicate entry 'db_identifier' for key 'name'")
        pass

    try:
        CustomField.objects.get_or_create(
            name="gcp_sql_instance_dbs",
            label="Google instance databases",
            type="STR",
            description="Used by the Google Cloud SQL blueprint",
            show_as_attribute=True,
            allow_multiple=True,
        )
    except IntegrityError:
        # IntegrityError: (1062, "Duplicate entry 'db_identifier' for key 'name'")
        pass


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
    instance_name = INSTANCE_NAME
    db_name = DB_NAME
    if db_name.isalnum() is False:
        raise CloudBoltException(
            f"Only alpha numeric characters (A-Z+0-9, case insensitive) are "
            f"allowed and the name provided was '{db_name}'."
        )
    if instance_name.isalnum() is False:
        raise CloudBoltException(
            f"Only alpha numeric characters (A-Z+0-9, case insensitive) are "
            f"allowed and the name provided was '{instance_name}'."
        )
    region = GCP_REGION
    root_password = ROOT_PASSWORD
    environment = Environment.objects.get(id=ENVIRONMENT)
    gcp_admin = GCPAdmin(environment)
    client = gcp_admin.storage_client

    # Store provisioning info to resource for teardown
    create_custom_fields()
    resource = kwargs.get("resource")
    resource.name = "Google Cloud SQL - " + instance_name
    resource.gcp_sql_instance_name = instance_name
    resource.gcp_sql_rh_id = gcp_admin.handler.id
    resource.gcp_sql_project = gcp_admin.project_name
    resource.save()

    try:
        inst_data = client.instances().list(
            project=gcp_admin.project_name).execute()

        if "items" in inst_data:
            instance_names = [inst["name"] for inst in inst_data["items"]]
            if instance_name in instance_names:
                return (
                    "ERROR",
                    'Server instance "%s" already exists' % instance_name,
                    "",
                )
    except HttpError as e:
        client_username = gcp_admin.client_email.split("@")[0]
        return (
            "ERROR",
            "Server instance {instance_name} could not be created ({reason}), "
            "make sure that this ResourceHandler's service account "
            "({service_account_name}) is given the Cloud SQL Admin "
            "Permission".format(
                instance_name=instance_name,
                reason=str(e),
                service_account_name=client_username,
            ),
            e,
        )

    # Create the Instance
    set_progress("\nCreating instance...")
    body = {
        "kind": "sql#instance",
        "name": instance_name,
        "project": gcp_admin.project_name,
        "region": region,
        "databaseVersion": DB_VERSION,
        "settings": {"tier": TIER},
        "rootPassword": root_password,
    }
    result = client.instances().insert(project=gcp_admin.project_name,
                                       body=body).execute()
    operation_id = result["name"]
    wait_for_operation(client, gcp_admin, operation_id)

    # Create the Database
    set_progress("\nNow attempting to create a new database...")
    body = {
        "kind": "sql#database",
        "name": db_name,
        "project": gcp_admin.project_name,
        "instance": instance_name,
    }

    result = client.databases().insert(project=gcp_admin.project_name,
                                       instance=instance_name,
                                       body=body).execute()
    set_progress(f'Database create result: {result}')
    operation_id = result["name"]
    wait_for_operation(client, gcp_admin, operation_id)

    set_progress(f"Database {db_name} is now available on instance:"
                 f" {instance_name}")

    store_instance_db_names(gcp_admin, instance_name, resource)