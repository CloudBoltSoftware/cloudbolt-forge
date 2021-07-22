from utilities.exceptions import CloudBoltException
from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler, GCPProject
from infrastructure.models import Environment
from google.oauth2.credentials import Credentials
from googleapiclient import discovery
import random
import json
import subprocess
import sys

RH_ID = "{{ gcp_resource_handler }}"
PROJECT_NAME = "{{ name }}"

def kebab_case(input_string):
    output_string = input_string
    output_string = output_string.lower()
    output_string = output_string.replace(" ", "-")
        
    while "--" in output_string:
        output_stirng = output_string.replace("--", "-")
    
    return output_string

def handle_completed_subprocess(completed_subprocess):
    if completed_subprocess.returncode != 0:
        if completed_subprocess.stderr:
            error_output = completed_subprocess.stderr.decode('utf-8').replace('\\n', '\n') 
            set_progress(f"error: {error_output}")
            raise CloudBoltException(error_output)
        else:
            raise CloudBoltException(f"subprocess {completed_subprocess} failed, no stderr detected")
    if completed_subprocess.stdout:
        standard_output = completed_subprocess.stdout.decode('utf-8').replace('\\n', '\n') 
        set_progress(completed_subprocess)


def run(job, *args, **kwargs):
    resource_handler_id = RH_ID
    new_project_name = PROJECT_NAME  
    new_project_id = f"{kebab_case(new_project_name)}-{random.randint(1000,9999)}"
    resource_handler = GCPHandler.objects.get(id=resource_handler_id)

    set_progress(f"Creating Project named {new_project_name} with id {new_project_id}")
    completed_project_creation_process = subprocess.run(['gcloud','projects','create', str(new_project_id), f'--name={new_project_name}'], capture_output=True)
    handle_completed_subprocess(completed_project_creation_process)
    

    completed_set_project_process = subprocess.run(['gcloud', 'config', 'set', 'project', new_project_id])
    handle_completed_subprocess(completed_set_project_process)

    set_progress("Enabling APIs required by CMP in order to import to CMP")
    completed_service_enable_process = subprocess.run(['gcloud', 'services', 'enable', 'cloudapis', 'compute', 'cloudresourcemanager'])
    handle_completed_subprocess(completed_service_enable_process)


    
    resource_handler.discover_projects()
    new_project_object = GCPProject.objects.get(id=new_project_id)
    new_project_number = new_project_object.project_number
    set_progress(f"Discovered that {new_project_id} has project number {new_project_number}")

    # credentials = Credentials(**json.loads(resource_handler.gcp_api_credentials))
    # serviceusage_service = discovery.build('serviceusage', 'v1', credentials=credentials)

    # enable_resource_cloud_apis_request = serviceusage_service.services().enable(name=f"projects/{new_project_number}/services/cloudapis.googleapis.com")
    # enable_resource_cloud_apis_response = enable_resource_cloud_apis_request.execute()
    
    # enable_serviceusage_request = serviceusage_service.services().enable(name=f"projects/{new_project_number}/services/serviceusage.googleapis.com")
    # enable_serviceusage_response = enable_serviceusage_request.execute()
    
    # enable_compute_request = serviceusage_service.services().enable(name=f"projects/{new_project_number}/services/compute.googleapis.com")
    # enable_compute_response = enable_compute_request.execute()

    # enable_cloudresourcemanager_request = serviceusage_service.services().enable(name=f"projects/{new_project_number}/services/cloudresourcemanager.googleapis.com")
    # enable_cloudresourcemanager_response = enable_cloudresourcemanager_request.execute()
    

    set_progress(f"Adding and importing new project {new_project_name} to {resource_handler.name}")
    token = json.loads(resource_handler.gcp_api_credentials)["token"]
    resource_handler.import_gcp_project(new_project_id, new_project_number, token)
    set_progress("Imported the new project, done!")

    
    return new_project_object

        
        
def generate_options_for_gcp_resource_handler(group=None, **kwargs):
    """
    List all GCP Handlers that are usable by the current group.
    """
    if not GCPHandler.objects.exists():
        raise CloudBoltException(
            "Ordering this Blueprint requires having a "
            "configured Google Cloud Platform resource handler."
            "and at least one Project added to the resource handler"
        )
        
    resource_handlers = GCPHandler.objects.all()
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform"
    ).select_related("resource_handler")

    
    if group:
        group_env_ids = [env.id for env in group.get_available_environments()]
        envs = envs.filter(id__in=group_env_ids)
        env_resource_handler_ids = {env.resource_handler_id for env in envs}
        resource_handlers = resource_handlers.filter(id__in=env_resource_handler_ids)
        
    return [(resource_handler.id, "{resource_handler}".format(resource_handler=resource_handler)) for resource_handler in resource_handlers]