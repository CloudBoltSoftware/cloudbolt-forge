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
        return ("FAILURE",
                "The environment used to create this cluster no longer exists",
                "")

    handler = environment.resource_handler.cast()
    project = environment.gcp_project

    gcp_project = GCPProject.objects.get(id=environment.gcp_project)
    service_account_key = json.loads(gcp_project.service_account_key)
    client_email = service_account_key.get('client_email')
    private_key = service_account_key.get('private_key')

    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': client_email,
        'private_key': private_key,
        'type': 'service_account',
        'client_id': None,
        'private_key_id': None,
    })

    client = build('container', 'v1', credentials=credentials)
    cluster_resource = client.projects().zones().clusters()

    # Delete cluster
    job.set_progress("Deleting cluster {}...".format(cluster_name))
    try:
        cluster_resource.delete(
            projectId=project, zone=zone, clusterId=cluster_name).execute()
    except HttpError as error:
        if error.resp['status'] == '404':
            return ("WARNING",
                    "Cluster {} was not found. It may have already been "
                    "deleted.".format(cluster_name),
                    "")
        raise

    # In CB 7.6 and before, this will delete any existing Kubernetes Resources.
    # Starting in CB 7.7, they will be marked HISTORICAL instead.
    kubernetes = Kubernetes.objects.get(id=resource.create_gke_k8s_cluster_id)
    kubernetes.delete()
