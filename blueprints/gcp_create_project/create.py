from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler
from infrastructure.models import Environment
import json
import random
from pprint import pprint
from googleapiclient import discovery
from google.oauth2.credentials import Credentials
import time

RH_ID = "{{ gcp_resource_handler }}"
PROJECT_NAME = "{{ name }}"

def kebab_case(input_string):
    output_string = input_string
    output_string = output_string.lower()
    output_string = output_string.replace(" ", "-")
        
    while "--" in output_string:
        output_stirng = output_string.replace("--", "-")
    
    return output_string

def run(job, *args, **kwargs):
    resource_handler_id = RH_ID
    new_project_name = PROJECT_NAME
    new_project_id = f"{kebab_case(new_project_name)}-{random.randint(100,999)}"
    set_progress(f" got resource handler id {resource_handler_id} and project name {new_project_name}")
    resource_handler = GCPHandler.objects.get(id=resource_handler_id)
    credentials = Credentials(**json.loads(resource_handler.gcp_api_credentials))
    service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
    user_agent = "google-cloud-sdk gcloud/313.0.1 command/gcloud.projects.create invocation-id/996da64d992742f4ae9b02b621ed2d06 environment/None environment-version/None interactive/True from-script/False python/3.6.4 term/xterm-256color (Macintosh; Intel Mac OS X 19.6.0)"

    project_body = {
        "name": new_project_name,
        "projectId": new_project_id ,
        "parent": {
            "type":"organization",
            "id":"789128875639"
        }
    }

    create_project_request = service.projects().create(body=project_body)
    set_progress(f"create_project_request: {create_project_request.__dict__}")
    create_project_request.headers["user-agent"] = user_agent
    create_project_response = create_project_request.execute()
    set_progress("Sent Project Creation Request to GCP, waiting for GCP")
    
    get_operation_request = service.operations().get(name=create_project_response["name"])
    set_progress(f"get_operation_request: {get_operation_request.__dict__}")
    get_operation_response = get_operation_request.execute()
    set_progress(f"get_operation_response: {get_operation_response}")
    
    while not get_operation_response.get("done", False):
        set_progress("Still waiting for GCP to finish creating the project...")
        time.sleep(2)
        get_operation_request = service.operations().get(**create_project_response)
        get_operation_response = get_operation_request.execute()

    new_project_number = get_operation_response["response"]["projectNumber"]
    new_project_object = resource_handler.add_gcp_project(new_project_id, new_project_name, new_project_number)
            
    ####
    serviceusage_service = discovery.build('serviceusage', 'v1', credentials=credentials)
    enable_serviceusage_request = serviceusage_service.services().enable(name=f"projects/{new_project_number}/services/serviceusage.googleapis.com")
    enable_serviceusage_response = enable_serviceusage_request.execute()
    ###

    
    try:
        set_progress(f"Adding and importing new project {new_project_name} to {resource_handler.name}")
        token = json.loads(resource_handler.gcp_api_credentials)["token"]
        resource_handler.import_gcp_project(new_project_id, new_project_number, token)
        set_progress("Imported the new project, done!")
    except Exception as err:
        set_progress("Encountered an error")
        delete_project_request = service.projects().delete(projectId=new_project_id)
        raise err
        
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