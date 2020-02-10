"""
Creates a Kubernetes cluster in Google Kubernetes Engine and adds it as a
Container Orchestrator in CloudBolt. Used by the Google Kubernetes Engine
blueprint.

To use this, you must have a Google Cloud Platform resource handler set up in
CloudBolt, and it must have a zone.

Takes 4 inputs:
    * GCP Project: the GCP Project (and CB env) to provision the cluster nodes in
    * GCP Zone: The zone in which the nodes should be placed
    * Cluster name: the name of the new cluster (must be unique)
    * Node count (optional): the number of nodes to provision (default=1)
"""
from __future__ import unicode_literals
import hashlib
import json
import random
import string
import time

from django.urls import reverse
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from containerorchestrators.models import ContainerOrchestratorTechnology
from containerorchestrators.kuberneteshandler.models import Kubernetes
from infrastructure.models import CustomField, Environment, Server
from orders.models import CustomFieldValue
from portals.models import PortalConfig
from resourcehandlers.gcp.models import GCPProject, GCPHandler
from utilities.exceptions import CloudBoltException

ENV_ID = '{{ gcp_project }}'
CLUSTER_NAME = '{{ name }}'
GCP_ZONE_ID = '{{ gcp_zone }}'
try:
    NODE_COUNT = int('{{ node_count }}')
except ValueError:
    NODE_COUNT = 1
TIMEOUT = 1800  # 30 minutes


class GKEClusterBuilder(object):
    def __init__(self, environment, zone, cluster_name):
        self.environment = environment
        self.cluster_name = cluster_name
        self.handler = environment.resource_handler.cast()
        self.zone = zone
        self.project = self.environment.gcp_project

        gcp_project = GCPProject.objects.get(id=self.environment.gcp_project)
        service_account_key = json.loads(gcp_project.service_account_key)
        client_email = service_account_key.get('client_email')
        private_key = service_account_key.get('private_key')

        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict({
            'client_email': client_email,
            'private_key': private_key,
            'type': 'service_account',
            'client_id': None,
            'private_key_id': None,
        })
        self.container_client = self.get_client('container')
        self.compute_client = self.get_client('compute')

    def get_client(self, serviceName, version='v1'):
        return build(serviceName, version, credentials=self.credentials)

    def create_cluster(self, node_count):
        cluster_resource = self.container_client.projects().zones().clusters()
        request = cluster_resource.create(
            projectId=self.project, zone=self.zone, body={
                'cluster': {
                    'name': self.cluster_name,
                    'initial_node_count': node_count,
                    'master_auth': {
                        'username': 'cloudbolt',
                        'password': ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=16)
                        )
                    }
                }
            })
        return request.execute()

    def get_cluster(self):
        cluster_resource = self.container_client.projects().zones().clusters()
        request = cluster_resource.get(
            projectId=self.project,
            zone=self.zone,
            clusterId=self.cluster_name,
        )
        return request.execute()

    def wait_for_endpoint(self, timeout=None):
        endpoint = None
        start = time.time()
        while not endpoint:
            if timeout is not None and (time.time() - start > timeout):
                break
            cluster = self.get_cluster()
            endpoint = cluster.get('endpoint')
            time.sleep(5)
        return endpoint

    def wait_for_nodes(self, node_count, timeout=None):
        nodes = []
        start = time.time()
        while len(nodes) < node_count:
            if timeout is not None and (time.time() - start > timeout):
                break
            request = self.compute_client.instances().list(
                project=self.project, zone=self.zone,
                filter="name:gke-{}-default-pool*".format(self.cluster_name))
            response = request.execute()
            nodes = response.get('items') or []
            time.sleep(5)
        return nodes

    def wait_for_running_status(self, timeout=None):
        status = ''
        start = time.time()
        while status != 'RUNNING':
            if timeout is not None and (time.time() - start > timeout):
                break
            cluster = self.get_cluster()
            status = cluster.get('status')
            time.sleep(5)
        return status


def generate_options_for_gcp_project(group=None, **kwargs):
    """
    List all GCP Projects that are orderable by the current group.
    """
    if not GCPHandler.objects.exists():
        raise CloudBoltException('Ordering this Blueprint requires having a '
                                 'configured Google Cloud Platform resource handler.')
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name='Google Cloud Platform') \
        .select_related('resource_handler')
    if group:
        group_env_ids = [env.id for env in group.get_available_environments()]
        envs = envs.filter(id__in=group_env_ids)
    return [
        (env.id, u'{env}'.format(env=env)) for env in envs
    ]


def generate_options_for_gcp_zone(group=None, **kwargs):
    """
    List all GCP zones.
    """
    field = CustomField.objects.get(name='gcp_zone')
    zones = CustomFieldValue.objects.filter(field=field)
    return [
        (zone.id, u'{zone}'.format(zone=zone)) for zone in zones
    ]


def create_required_parameters():
    CustomField.objects.get_or_create(
        name='create_gke_k8s_cluster_project',
        defaults=dict(
            label="GKE Cluster: Project",
            description="Used by the GKE Cluster blueprint",
            type="INT"
        ))
    CustomField.objects.get_or_create(
        name='create_gke_k8s_cluster_name',
        defaults=dict(
            label="GKE Cluster: Cluster Name",
            description="Used by the GKE Cluster blueprint",
            type="STR"
        ))
    CustomField.objects.get_or_create(
        name='create_gke_k8s_cluster_id',
        defaults=dict(
            label="GKE Cluster: Cluster ID",
            description="Used by the GKE Cluster blueprint",
            type="INT",
        ))


def run(job=None, logger=None, **kwargs):
    """
    Create a cluster, poll until the IP address becomes available, and import
    the cluster into CloudBolt.
    """
    environment = Environment.objects.get(id=ENV_ID)
    gcp_zone = CustomFieldValue.objects.get(id=GCP_ZONE_ID).value

    # Save cluster data on the resource so teardown works later
    create_required_parameters()
    resource = kwargs['resource']
    resource.create_gke_k8s_cluster_project = environment.id
    resource.gcp_zone = gcp_zone
    resource.create_gke_k8s_cluster_name = CLUSTER_NAME
    resource.name = CLUSTER_NAME
    resource.save()

    job.set_progress('Connecting to GKE...')
    builder = GKEClusterBuilder(environment, gcp_zone, CLUSTER_NAME)

    job.set_progress('Sending request for new cluster {}...'.format(CLUSTER_NAME))
    builder.create_cluster(NODE_COUNT)

    job.set_progress('Waiting up to {} seconds for provisioning to complete.'
                     .format(TIMEOUT))
    start = time.time()
    job.set_progress('Waiting for cluster IP address...')
    endpoint = builder.wait_for_endpoint(timeout=TIMEOUT)
    if not endpoint:
        return ("FAILURE",
                "No IP address returned after {} seconds".format(TIMEOUT),
                "")

    remaining_time = TIMEOUT - (time.time() - start)
    job.set_progress('Waiting for nodes to report hostnames...')
    nodes = builder.wait_for_nodes(NODE_COUNT, timeout=remaining_time)
    if len(nodes) < NODE_COUNT:
        return ("FAILURE",
                "Nodes are not ready after {} seconds".format(TIMEOUT),
                "")

    job.set_progress('Importing cluster...')
    cluster = builder.get_cluster()
    tech = ContainerOrchestratorTechnology.objects.get(name='Kubernetes')
    kubernetes = Kubernetes.objects.create(
        name=CLUSTER_NAME,
        ip=cluster['endpoint'],
        port=443,
        protocol='https',
        serviceaccount=cluster['masterAuth']['username'],
        servicepasswd=cluster['masterAuth']['password'],
        container_technology=tech,
    )
    resource.create_gke_k8s_cluster_id = kubernetes.id
    resource.save()
    url = 'https://{}{}'.format(
        PortalConfig.get_current_portal().domain,
        reverse('container_orchestrator_detail', args=[kubernetes.id])
    )
    job.set_progress("Cluster URL: {}".format(url))

    job.set_progress('Importing nodes...')
    for node in nodes:
        # Generate libcloud UUID from GCE ID
        id_unicode = '{}:{}'.format(node['id'], 'gce')
        uuid = hashlib.sha1(id_unicode.encode('utf-8')).hexdigest()
        # Create a barebones server record. Other details like CPU and Mem Size
        # will be populated the next time the GCE handler is synced.
        Server.objects.create(
            hostname=node['name'],
            resource_handler_svr_id=uuid,
            environment=environment,
            resource_handler=environment.resource_handler,
            group=resource.group,
            owner=resource.owner,
        )

    job.set_progress('Waiting for cluster to report as running...')
    remaining_time = TIMEOUT - (time.time() - start)
    status = builder.wait_for_running_status(timeout=remaining_time)
    if status != 'RUNNING':
        return ("FAILURE",
                "Status is {} after {} seconds (expected RUNNING)".format(
                    status, TIMEOUT),
                "")

    return ("SUCCESS",
            "Cluster is ready and can be accessed at {}".format(url),
            "")
