"""
Deletes the Kubernetes cluster associated with this service. Used by the
Google Kubernetes Engine blueprint.
"""
from __future__ import unicode_literals

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from containerorchestrators.kuberneteshandler.models import Kubernetes
from infrastructure.models import Environment


def run(job=None, logger=None, resource=None, **kwargs):
    # Get cluster information
    cluster_name = resource.create_gke_k8s_cluster_name
    if not cluster_name:
        return "WARNING", "No cluster associated with this resource", ""
    env_id = resource.create_gke_k8s_cluster_env
    try:
        environment = Environment.objects.get(id=env_id)
    except Environment.DoesNotExist:
        return ("FAILURE",
                "The environment used to create this cluster no longer exists",
                "")
    handler = environment.resource_handler.cast()
    project = handler.gcp_projects
    zone = environment.gcp_zone

    # Get client
    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': handler.serviceaccount,
        'private_key': handler.servicepasswd,
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
