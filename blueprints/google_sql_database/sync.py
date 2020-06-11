"""
Discover Mysql records with some identifying attributes on GCP
return a list of dictionaries from the 'discover_resoures' function
"""
import json

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from resourcehandlers.gcp.models import GCPProject, GCPHandler


RESOURCE_IDENTIFIER = ["gcp_sql_instance_name", "gcp_sql_project"]


def discover_resources(**kwargs):
    discovered_mysqldb = []

    existing_instances = set()
    existing_bps = ServiceBlueprint.objects.filter(
        name__contains="Google MySQL Database"
    )

    for bp in existing_bps:
        for resource in bp.resource_set.filter(lifecycle="ACTIVE"):
            existing_instances.add(
                (resource.gcp_sql_instance_name, resource.gcp_sql_project)
            )

    for project in GCPProject.objects.filter(imported=True):
        try:
            account_info = json.loads(project.service_account_key)
        except:  # noqa: E722
            account_info = json.loads(project.service_account_info)

        environment = project.environment  # noqa: F841
        resource_handler = project.handler
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(account_info)
        client_email = account_info["client_email"]
        set_progress(
            "Connecting to Google Cloud through service account email {}".format(
                client_email
            )
        )
        set_progress("RH: %s" % resource_handler.name)
        service_name = "sqladmin"
        version = "v1beta4"
        client = build(service_name, version, credentials=credentials)

        try:
            instances = (
                client.instances().list(project=project.id).execute().get("items", None)
            )
            if instances:
                for instance in instances:
                    set_progress(
                        "Found Database named {}: checking to see if the instance already exists on CB".format(
                            instance["name"]
                        )
                    )
                    if (instance["name"], project.name) not in existing_instances:
                        discovered_mysqldb.append(
                            {
                                "name": instance["name"],
                                "gcp_sql_instance_name": instance["name"],
                                "gcp_sql_rh_id": resource_handler.id,
                                "gcp_sql_project": project.name,
                            }
                        )
        except Exception as e:
            set_progress(
                "Could not list sql servers for {}, error message is as follows:{}".format(
                    project.name, e
                )
            )
    return discovered_mysqldb
