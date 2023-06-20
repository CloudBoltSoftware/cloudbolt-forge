"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress


import json
import hashlib

from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

from infrastructure.models import Environment
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler
from infrastructure.models import Server
from servicecatalog.models import ServiceBlueprint
from resources.models import Resource as Resource_gke, ResourceType
from accounts.models import Group


RESOURCE_IDENTIFIER = 'create_gke_k8s_cluster_name'


def discover_resources(**kwargs):
    discovered_google_gke_clusters = []
    
    #create a set of all projects
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    projects = {env.gcp_project for env in gcp_envs}
    
    group = Group.objects.filter(name__icontains='unassigned').first()
    blueprint = ServiceBlueprint.objects.filter(name__icontains="Google Kubernetes Engine Cluster").first()
    resource_type = ResourceType.objects.filter(name__icontains="cluster").first()
    
    for handler in GCPHandler.objects.all():
        set_progress('Connecting to Google Kubernetics Engine Cluster for \
                      handler: {}'.format(handler))
        
        #only get gke clusters of projects in the set
        for env in Environment.objects.filter(resource_handler_id=handler.id):
            project_id = env.gcp_project
            if project_id not in projects:
                continue

            container_wrapper = create_gke_api_wrapper(handler, "container")
            if not container_wrapper:
                set_progress("Could not connect to Google Cloud.  Skipping this resource handler.")
                continue

            set_progress("Connection to Google Cloud established")
            
            gcp_project = handler.gcp_projects.get(id = project_id).gcp_id
            clusters = list_gke_clusters(container_wrapper, gcp_project).get("clusters", None)
            if not clusters:
                set_progress("No resource are vailable to sync")
                return []
            compute_wrapper = create_gke_api_wrapper(handler, "compute")
        
            for cluster in clusters:
                if cluster.get("name"):
                    nodes = list_gke_nodes(compute_wrapper, gcp_project, cluster['zone'], cluster['name']).get("items", None)
                    resource = Resource_gke.objects.filter(name__exact = cluster['name'], lifecycle = 'ACTIVE').first()
                    if not resource:
                        resource = Resource_gke.objects.create(
                            name=cluster['name'],
                            blueprint=blueprint,
                            group=group,
                            resource_type=resource_type,
                        )
                        set_progress(f"Creating new resource {cluster['name']}")
                    # Store the resource handler's ID on this resource so the teardown action
                    # knows which credentials to use.
                    resource.google_rh_id = handler.id
                    resource.lifecycle = 'ACTIVE'
                    resource.create_gke_k8s_cluster_name = cluster.get("name", "noName")
                    resource.created_at = cluster['createTime']
                    resource.kubernetes_version = cluster['initialClusterVersion']
                    resource.endpoint = cluster['endpoint']
                    resource.status = cluster['status']
                    resource.project_id =  gcp_project
                    resource.create_gke_k8s_cluster_project = env.id
                    resource.gcp_zone = cluster['zone']
                    for node in nodes:
                            id_unicode = '{}:{}'.format(node['id'], 'gcp')
                            uuid = hashlib.sha1(id_unicode.encode('utf-8')).hexdigest()
                            try:
                                serv = Server.objects.get(hostname=node['name'])
                            except Server.DoesNotExist:
                                serv = None
                            
                            if not serv:
                                serv = Server.objects.create(hostname=node['name'],
                                        resource_handler_svr_id=uuid,
                                        environment=env,
                                        resource_handler=env.resource_handler,
                                        group=resource.group)
                                
                                server = Server.objects.get(hostname=node['name'])
                                resource.server_set.add(server)     
                    resource.save()
            #remove project from the set after getting its clusters
            projects.discard(project_id)

    return []


def list_gke_clusters(wrapper: Resource, project_id: str) -> dict:
    """
    Get all gke clusters in a given project
    https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.zones.clusters/list
    """
    clusters_list_request = wrapper.projects().zones().clusters().list(projectId=project_id, zone='-')
    return clusters_list_request.execute()
    
def list_gke_nodes(wrapper: Resource, project_id: str, zone : str, cluster_name: str) -> dict:
    """
    Get all gke nodes in a given project
    https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.zones.clusters/list
    """
    nodes_list_request = wrapper.instances().list(project=project_id, zone=zone, filter="name:gke-{}-default-pool*".format(cluster_name))
    return nodes_list_request.execute()


def create_gke_api_wrapper(gcp_handler: GCPHandler, service: str) -> Resource:
    """
    Using googleapiclient.discovery, build the api wrapper for the gke cluster
    """
    if not gcp_handler.gcp_api_credentials:
        set_progress("Could not find Google Cloud credentials for this reource handler.")
        return None
    credentials_dict = json.loads(gcp_handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    gke_wrapper: Resource = build(service, "v1", credentials=credentials, cache_discovery=False)
    return gke_wrapper