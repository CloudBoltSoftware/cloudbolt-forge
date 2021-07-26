import json
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

from infrastructure.models import Environment
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler


RESOURCE_IDENTIFIER = 'instance_name'


def discover_resources(**kwargs):
    discovered_google_bigtables = []
    
    #create a set of all projects
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    projects = {env.GCP_project for env in gcp_envs}

    for handler in GCPHandler.objects.all():
        set_progress('Connecting to Google BigTable for \
                      handler: {}'.format(handler))
        
        #only get bigtables of projects in the set
        for env in Environment.object.filter(resource_handler_id=handler.id):
            project = env.GCP_project
            if project not in projects:
                continue

            wrapper = create_bigtable_api_wrapper(handler)
            if not wrapper:
                set_progress("Could not connect to Google Cloud.  Skipping this resource handler.")
                continue

            set_progress("Connection to Google Cloud established")
            instances = list_bigtables(wrapper, project).get("instances", None)

            for bigtable in instances():
                if bigtable.get("displayName"):
                    discovered_google_bigtables.append(
                        {
                            'name': bigtable.get("displayName", "noName"),
                            'instance_name': bigtable.get("displayName", "noName"),
                            'google_rh_id': handler.id,
                        }
                    )
            #remove project from the set after getting its bigtables
            projects.discard(project)

    return discovered_google_bigtables


def list_bigtables(wrapper: Resource, project_id: str) -> dict:
    """
    Get all bigtable instances in a given project
    https://cloud.google.com/bigtable/docs/reference/admin/rest/v2/projects.instances/list
    """
    proj_str = f"projects/{project_id}"
    inst_list_request = wrapper.projects().instances().list(parent=proj_str)
    return inst_list_request.execute()


def create_bigtable_api_wrapper(gcp_handler: GCPHandler) -> Resource:
    """
    Using googleapiclient.discovery, build the api wrapper for the bigtableadmin api:
    https://googleapis.github.io/google-api-python-client/docs/dyn/bigtableadmin_v2.projects.instances.html
    """
    if not gcp_handler.gcp_api_credentials:
        set_progress("Could not find Google Cloud credentials for this reource handler.")
        return None
    credentials_dict = json.loads(gcp_handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    bigtable_wrapper: Resource = build("bigtableadmin", "v2", credentials=credentials, cache_discovery=False)
    return bigtable_wrapper
