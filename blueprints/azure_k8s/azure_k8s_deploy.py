"""
Install the following packages on your CB:
  pip install kubernetes
  pip install azure-cli

Install kubectl:
  az aks install-cli

Configure Azure login creds:
  az login        # this is a one time process

Confirm cluster access:
  az aks list  - # lists all clusters

"""

from __future__ import unicode_literals
import hashlib
import time

from django.urls import reverse
from kubernetes.client import Configuration, ApiClient
from kubernetes import config, client
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources.models import ResourceGroup
from azure.mgmt.containerservice.models import ManagedClusterAgentPoolProfile
from azure.mgmt.containerservice.models import ManagedCluster
from containerorchestrators.models import ContainerOrchestratorTechnology
from containerorchestrators.kuberneteshandler.models import Kubernetes
from azure.mgmt.containerservice import ContainerServiceClient
from infrastructure.models import CustomField, Environment, Server
from portals.models import PortalConfig
from common.methods import set_progress
from utilities.exceptions import CloudBoltException
from msrestazure.azure_exceptions import CloudError
from resources.models import ResourceType, Resource
from azure.mgmt.containerservice.models import ManagedClusterServicePrincipalProfile
import subprocess
import yaml
import json
from threading import Timer
from msrest.polling import *

ENV_ID = '{{ cloudbolt_environment }}'
resource_group = '{{ resource_groups }}'
dns_prefix = '{{ cluster_dns_prefix }}'
agent_pool_name = '{{ cluster_pool_name}}'
CLUSTER_NAME = '{{ cluster_name }}'

try:
    environment = Environment.objects.get(id=ENV_ID)
    handler = environment.resource_handler.cast()
    client_id = handler.client_id
    secret = handler.secret
    location = handler.get_env_location(environment)
except:
    set_progress("Couldn't get environment.")

service = "lb-front"
image = 'nginx:1.15'

try:
    NODE_COUNT = int('{{ node_count }}')
except ValueError:
    NODE_COUNT = 1
TIMEOUT = 600  # 10 minutes


def get_credentials():
    creds = ServicePrincipalCredentials(
        client_id=handler.client_id,
        secret=handler.secret,
        tenant=handler.tenant_id,
    )
    return creds


def get_service_profile():
    profile = ManagedClusterServicePrincipalProfile(
        client_id=handler.client_id,
        secret=handler.secret,
    )
    return profile


def get_resource_client():
    credentials = get_credentials()
    subscription_id = handler.serviceaccount
    resource_client = ResourceManagementClient(credentials, subscription_id)
    return resource_client


def get_container_client():
    subscription_id = handler.serviceaccount
    credentials = get_credentials()
    container_client = ContainerServiceClient(credentials, subscription_id)
    return container_client


def create_resource_group():
    resource_client = get_resource_client()
    result = resource_client.resource_groups.create_or_update(
        resource_group,
        parameters=ResourceGroup(
            location=location,
            tags={},
        )
    )
    return result


def create_cluster(node_count):
    """
    Azure requires node pool name to be 9 alphanumeric characters, and lowercase.
    """
    profile = get_service_profile()
    container_client = get_container_client()
    cluster_resource = container_client.managed_clusters.create_or_update(
        resource_group,
        CLUSTER_NAME,
        parameters=ManagedCluster(
            location=location,
            tags=None,
            dns_prefix=dns_prefix.lower(),
            service_principal_profile=profile,
            agent_pool_profiles=[{
                'name': agent_pool_name.lower()[:9],
                'vm_size': 'Standard_DS2_v2',
                'count': node_count,
            }],
        ),
    )
    return cluster_resource


def create_deployment_object():
    """
    Creates the LB service and exposes the external IP
    """
    container = client.V1Container(
        name="my-nginx",
        image="nginx:1.15",
        ports=[client.V1ContainerPort(container_port=80)])
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "nginx"}),
        spec=client.V1PodSpec(containers=[container]))
    spec = client.ExtensionsV1beta1DeploymentSpec(
        replicas=1,
        template=template)
    set_progress("Instantiate the deployment object")
    deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name="nginx-deployment"),
        spec=spec)
    time.sleep(60)
    return deployment


def create_deployment(api_instance, deployment):
    api_response = api_instance.create_namespaced_deployment(body=deployment, namespace="default")
    time.sleep(60)
    return ("SUCCESS", "Deployment created. Status={}".format(api_response.status), "")


def create_service():
    api = client.CoreV1Api()
    body = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': service,
        },
        'spec': {
            'type': 'LoadBalancer',
            'selector': {
                'app': service,
            },
            'ports': [
                client.V1ServicePort(port=80, target_port=80),
            ],
            'restartPolicy': 'Never',
            'serviceAccountName': "default",
        }
    }
    result = api.create_namespaced_service(namespace='default', body=body)
    return result


def get_cluster():
    result = subprocess.check_output(['az', 'aks', 'show', '-g', resource_group, '-n', CLUSTER_NAME, '-o', 'json'])
    res = json.loads(result)
    cluster = res['name']
    return cluster


def get_cluster_endpoint():
    '''
    Get kubernetes services and Load balancer endpoint from shell
    '''
    cluster = subprocess.check_output("kubectl get service -o json".split())
    res = json.loads(cluster)
    endpoint = res['items'][1]['status']['loadBalancer']['ingress'][0]['ip']
    return endpoint


def wait_for_endpoint(timeout=None):
    '''
    Wait for load balancer external IP to be created
    '''
    endpoint = None
    start = time.time()
    while not endpoint:
        if timeout is not None and (time.time() - start > timeout):
            break
        endpoint = get_cluster_endpoint()
    return endpoint


def get_nodes():
    node = subprocess.check_output("kubectl get nodes -o json".split())
    res = json.loads(node)
    result = res['items']
    nodes = []
    for item in result:
        response = item["status"]["addresses"][1]["address"]
        nodes.append(response)
    return nodes


def wait_for_nodes(node_count, timeout=None):
    result = get_nodes()
    nodes = []
    start = time.time()
    while len(nodes) < node_count:
        if timeout is not None and (time.time() - start > timeout):
            break
        nodes = result or []
    return nodes

def wait_for_running_status(timeout=None):
    # Check and wait for build status of cluster and work node builds
    status = ''
    start = time.time()
    while status != "Succeeded":
        set_progress("waiting for SUCCEED status of cluster build")
        if status == 'Failed':
            raise CloudBoltException("Deployment failed")
        if timeout is not None and (time.time() - start > timeout):
            break
        cluster = subprocess.check_output(['az', 'aks', 'show', '-g', resource_group, '-n', CLUSTER_NAME, '-o', 'json'])
        res = json.loads(cluster)
        status = res['provisioningState']
    return status

def generate_options_for_cloudbolt_environment(group=None, **kwargs):
    # List all Azure environments that are orderable by the current group
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name='Azure') \
        .select_related('resource_handler')
    if group:
        group_env_ids = [env.id for env in group.get_available_environments()]
        envs = envs.filter(id__in=group_env_ids)
    return [
        (env.id, u'{env} ({region})'.format(
            env=env, region=env.resource_handler.cast()))
        for env in envs
    ]


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label': 'Azure RH ID',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='aks_cluster_env', type='INT',
        defaults={'label': 'AKS Cluster: Environment',
                  'description': 'Used by the AKS Cluster blueprint', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='aks_cluster_name', type='STR',
        defaults={'label': 'AKS Cluster: Cluster Name',
                  'description': 'Used by the AKS Cluster blueprint', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='aks_cluster_id',
        defaults=dict(
            label="AKS Cluster: Cluster ID",
            description="Used by the AKS Cluster blueprint",
            type="INT",
        ))
    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label': 'Azure Location',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label': 'Azure Resource Group',
                  'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )


def run(job=None, logger=None, **kwargs):
    """
    Create a cluster, poll until the IP address becomes available, and import
    the cluster into CloudBolt.
    """
    cluster_env = AzureARMHandler.objects.first()
    # Save cluster data on the resource so teardown works later
    create_custom_fields()
    resource = kwargs['resource']

    resource.name = CLUSTER_NAME
    resource.aks_cluster_env = cluster_env.id
    resource.resource_group_name = resource_group
    resource.aks_cluster_name = CLUSTER_NAME
    resource.save()

    get_credentials()
    get_service_profile()
    get_resource_client()
    get_container_client()
    get_service_profile()

    # Clusters can be created in existing resource groups.
    job.set_progress("Checking if Resource Group Exists {}".format(resource_group))
    rg_client = get_resource_client()
    response = rg_client.resource_groups.check_existence(resource_group)
    if response == True:
        job.set_progress("Resource Group: {} already exits. Cluster {} will be created in {}".format(resource_group, CLUSTER_NAME, resource_group))

    job.set_progress("Creating Resource Group {}".format(resource_group))
    create_resource_group()

    # Checks for existing cluster in the Resource Group and fails if exists
    job.set_progress("Creating Cluster {}".format(CLUSTER_NAME))
    try:
        create_cluster(NODE_COUNT)
    except CloudError as e:
        if e.status_code == 409:
            return ("FAILURE", "Cluster: {} conflicts with existing cluster ".format(CLUSTER_NAME), "")

        raise

    start = time.time()
    remaining_time = TIMEOUT - (time.time() - start)

    status = wait_for_running_status()
    job.set_progress('Waiting up to {} seconds for provisioning to complete.'
                         .format(remaining_time))
    job.set_progress("Configuring kubectl to connect to kubernetes cluster")

    # configure kubectl to connect to kubernetes cluster
    subprocess.run(['az', 'aks', 'get-credentials', '-g', resource_group, '-n', CLUSTER_NAME])
    start = time.time()

    config.load_kube_config()

    job.set_progress("Creating pod template container")
    api_instance = client.ExtensionsV1beta1Api()

    deployment = create_deployment_object()

    job.set_progress("Creating Deployment")
    create_deployment(api_instance, deployment)

    job.set_progress("Creating Service {}".format(service))
    create_service()

    job.set_progress("Waiting for cluster IP address...")
    endpoint = wait_for_endpoint()
    if not endpoint:
        return ("FAILURE", "No IP address returned",
                "")
    remaining_time = TIMEOUT - (time.time() - start)
    job.set_progress('Waiting for nodes to report hostnames...')

    nodes = wait_for_nodes(NODE_COUNT)
    if len(nodes) < NODE_COUNT:
        return ("FAILURE",
                "Nodes are not ready after {} seconds",
                "")

    job.set_progress('Importing cluster...')

    get_cluster()
    tech = ContainerOrchestratorTechnology.objects.get(name='Kubernetes')
    kubernetes = Kubernetes.objects.create(
        name=CLUSTER_NAME,
        ip=endpoint,
        port=443,
        protocol='https',
        serviceaccount=handler.serviceaccount,
        servicepasswd=handler.secret,
        container_technology=tech,
    )

    resource.aks_cluster_id = kubernetes.id
    resource.save()
    url = 'https://{}{}'.format(
        PortalConfig.get_current_portal().domain,
        reverse('container_orchestrator_detail', args=[kubernetes.id])
    )
    job.set_progress("Cluster URL: {}".format(url))

    job.set_progress('Importing nodes...')

    job.set_progress('Waiting for cluster to report as running...')
    remaining_time = TIMEOUT - (time.time() - start)

    return ("SUCCESS","Cluster is ready and can be accessed at {}".format(url), "")
