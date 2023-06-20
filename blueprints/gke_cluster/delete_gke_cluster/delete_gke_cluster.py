"""
Deletes the Kubernetes cluster associated with this service. Used by the
Google Kubernetes Engine blueprint.
"""
from __future__ import unicode_literals

import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from containerorchestrators.kuberneteshandler.models import Kubernetes
from infrastructure.models import Environment
from resourcehandlers.gcp.models import GCPProject
from google.oauth2.credentials import Credentials
from common.methods import set_progress


def run(job=None, logger=None, resource=None, **kwargs):
    # Get cluster information
    cluster_name = resource.create_gke_k8s_cluster_name
    zone = resource.gcp_zone

    if not cluster_name:
        return "WARNING", "No cluster associated with this resource", ""
    if not zone:
        return "WARNING", "No GCP Zone associated with this resource", ""

    project_id = resource.create_gke_k8s_cluster_project
    try:
        environment = Environment.objects.get(id=project_id)
    except Environment.DoesNotExist:
        return (
            "FAILURE",
            "The environment used to create this cluster no longer exists",
            "",
        )

    handler = environment.resource_handler.cast()
    project_id = environment.gcp_project

    gcp_project_name = GCPProject.objects.get(id=environment.gcp_project).gcp_id
    
    api_key = getattr(handler, "gcp_api_credentials", None)
    
    if not api_key:
        try:
            service_account_key = json.loads(project_id.service_account_info)
        except Exception:
            service_account_key = json.loads(project_id.service_account_key)

        client_email = service_account_key.get("client_email")
        private_key = service_account_key.get("private_key")

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            {
                "client_email": client_email,
                "private_key": private_key,
                "type": "service_account",
                "client_id": None,
                "private_key_id": None,
            }
        )
    else:
        set_progress("Using the API Key in the resource handler")
        set_progress("Make sure your OAuth account has permission to edit GKE Nodes")
        credentials = Credentials(**json.loads(api_key))

    client = build("container", "v1", credentials=credentials)
    cluster_resource = client.projects().zones().clusters()

    # Delete cluster
    job.set_progress("Deleting cluster {}...".format(cluster_name))
    try:
        cluster_resource.delete(
            projectId=gcp_project_name, zone=zone, clusterId=cluster_name
        ).execute()
    except HttpError as error:
        if error.resp["status"] == "404":
            return (
                "WARNING",
                "Cluster {} was not found. It may have already been "
                "deleted.".format(cluster_name),
                "",
            )
        raise

    try:
        kubernetes = Kubernetes.objects.get(id=resource.container_orchestrator_id)
        kubernetes.delete()
    except Kubernetes.DoesNotExist:
        pass
