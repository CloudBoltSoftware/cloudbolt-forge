"""
Plug-in for creating a Google SQL database.
"""
from __future__ import unicode_literals

import json

from django.db import IntegrityError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from infrastructure.models import CustomField, Environment
from common.methods import set_progress
import time

from resourcehandlers.gcp.models import GCPHandler

SQL_VALID_REGIONS = [
    "northamerica-northeast1",
    "us-central",
    "us-central1",
    "us-east1",
    "us-east4",
    "us-west1",
    "us-west2",
    "southamerica-east1",
    "europe-north1",
    "europe-west1",
    "europe-west2",
    "europe-west3",
    "europe-west4",
    "europe-west6",
    "asia-east1",
    "asia-east2",
    "asia-northeast1",
    "asia-northeast2",
    "asia-south1",
    "asia-southeast1",
    "australia-southeast1",
]

ENVIRONMENT = {{env_id}}
DB_NAME = "{{db_identifier}}"
DB_VERSION = "{{db_version}}"
GCP_REGION = "{{gcp_region}}"


def generate_options_for_gcp_region(**kwargs):
    return [(region, region) for region in SQL_VALID_REGIONS]


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
        ("MYSQL_5_7", "My SQL version 5.7"),
        ("MYSQL_5_6", "My SQL version 5.6"),
        ("POSTGRES_9_6", "PostgreSQL version 9.6"),
        ("POSTGRES_11", "PostgreSQL version 11"),
    ]


def run(job=None, logger=None, **kwargs):
    """
    """
    db_name = DB_NAME
    instance_name = db_name

    environment = Environment.objects.get(id=ENVIRONMENT)
    rh = environment.resource_handler.cast()
    assert isinstance(rh, GCPHandler)
    project = environment.gcp_project
    region = GCP_REGION
    set_progress("REGION: %s" % GCP_REGION)

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

    resource = kwargs.get("resource")
    resource.name = "Google SQL - " + instance_name
    resource.gcp_sql_instance_name = instance_name
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.gcp_sql_rh_id = rh.id
    resource.gcp_sql_project = project
    resource.save()

    try:
        account_info = json.loads(rh.gcp_projects.get(id=project).service_account_info)
    except Exception:
        account_info = json.loads(rh.gcp_projects.get(id=project).service_account_key)

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(account_info)

    job.set_progress(
        "Connecting to Google Cloud through service account email {}".format(
            account_info["client_email"]
        )
    )
    set_progress("RH: %s" % rh)

    service_name = "sqladmin"
    version = "v1beta4"
    client = build(service_name, version, credentials=credentials)

    set_progress("Connection established")

    try:
        inst_data = client.instances().list(project=project).execute()

        if "items" in inst_data:
            instance_names = [inst["name"] for inst in inst_data["items"]]
            if instance_name in instance_names:
                return (
                    "ERROR",
                    'Server instance "%s" already exists' % instance_name,
                    "",
                )
    except HttpError as e:
        client_username = account_info["client_email"].split("@")[0]
        return (
            "ERROR",
            "Server instance {instance_name} could not be created ({reason}), make sure that this ResourceHandler's service account ({service_account_name}) is given the Cloud SQL Admin Permission".format(
                instance_name=instance_name,
                reason=str(e),
                service_account_name=client_username,
            ),
            e,
        )

    set_progress("\nCreating instance...")

    body = {
        "kind": "sql#instance",
        "name": instance_name,
        "project": project,
        "region": region,
        "databaseVersion": DB_VERSION,
        "settings": {"tier": "db-n1-standard-1"},
    }
    result = client.instances().insert(project=project, body=body).execute()

    # Wait the server instance to be created:
    while True:
        inst_data = client.instances().list(project=project).execute()
        status = None
        for inst in inst_data["items"]:
            if inst["name"] == instance_name:
                status = inst["state"]
                break
        set_progress("Status of the server instance is: %s" % status)
        if status == "RUNNABLE":
            break
        time.sleep(2)

    set_progress("\nNow attempting to create a new database...")

    body = {
        "kind": "sql#database",
        "name": db_name,
        "project": project,
        "instance": instance_name,
    }

    result = (
        client.databases()
        .insert(project=project, instance=instance_name, body=body)
        .execute()
    )
    assert result["status"] == "DONE"

    set_progress(
        "Database %s is now available on instance: %s" % (db_name, instance_name)
    )
