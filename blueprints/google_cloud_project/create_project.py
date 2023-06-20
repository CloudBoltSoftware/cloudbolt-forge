import json
import random
import time

from googleapiclient import discovery
from google.oauth2.credentials import Credentials

from common.methods import set_progress
from resourcehandlers.gcp.models import GCPHandler
from infrastructure.models import Environment
from utilities.exceptions import CloudBoltException


def kebab_case(input_string):
    output_string = input_string
    output_string = output_string.lower()
    output_string = output_string.replace(" ", "-")

    while "--" in output_string:
        output_string = output_string.replace("--", "-")

    return output_string


def execute_and_wait(service, request, sleep=10, timeout=300):
    timeout_time = time.time() + timeout
    set_progress(f"Request: {request.__dict__}")
    response = request.execute()
    set_progress(f"Sent Request to GCP's {service._baseUrl}, waiting for response...")

    if not hasattr(service, "operations"):
        return response

    get_operation_request = service.operations().get(**response)
    set_progress(f"get_operation_request: {get_operation_request.__dict__}")
    get_operation_response = get_operation_request.execute()
    set_progress(f"get_operation_response: {get_operation_response}")

    while not get_operation_response.get("done", False):
        if time.time() > timeout_time:
            raise CloudBoltException(
                f"{service._baseUrl} operation did not complete in the maximun allowed time of {timeout} seconds"
            )
        set_progress(f"Still waiting for GCP to finish executing the request {service._baseUrl}...")
        time.sleep(sleep)
        get_operation_request = service.operations().get(**response)
        get_operation_response = get_operation_request.execute()

    return get_operation_response


def run(job, *args, **kwargs):
    resource_handler_id = "{{ gcp_resource_handler }}"
    new_project_name = "{{ name }}"
    billing_name = "{{ billing_name }}"
    new_project_id = f"{kebab_case(new_project_name)}-{random.randint(100, 999)}"
    set_progress(
        f" got resource handler id {resource_handler_id} and project name {new_project_name}")
    resource_handler = GCPHandler.objects.get(id=resource_handler_id)
    credentials = Credentials(**json.loads(resource_handler.gcp_api_credentials))

    # create project
    service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials,
                              cache_discovery=False)
    body = {
        "name": new_project_name,
        "projectId": new_project_id
    }

    request = service.projects().create(body=body)
    get_operation_response = execute_and_wait(service, request, sleep=2)
    
    set_progress(f"get_operation_response: {get_operation_response} ")
    
    if "error" in get_operation_response.keys():
        raise CloudBoltException("You do not have permission to create projects within this organization")
    
    new_project_number = get_operation_response["response"]["projectNumber"]
    new_project_object = resource_handler.add_gcp_project(new_project_id, new_project_name,
                                                          new_project_number)

    # enable billing
    service = discovery.build('cloudbilling', 'v1', credentials=credentials, cache_discovery=False)
    body = {
        "projectId": new_project_id,
        "billingAccountName": billing_name,
    }
    request = service.projects().updateBillingInfo(name=f"projects/{new_project_id}", body=body)
    execute_and_wait(service, request)

    # enable compute
    service = discovery.build('serviceusage', 'v1', credentials=credentials, cache_discovery=False)
    request = service.services().enable(
        name=f"projects/{new_project_id}/services/compute.googleapis.com")
    execute_and_wait(service, request)

    # create all necessary CloudBolt objects
    set_progress(
        f"Adding and importing new project {new_project_name} to {resource_handler.name}")
    token = json.loads(resource_handler.gcp_api_credentials)["token"]
    new_gcp_project = resource_handler.add_gcp_project(new_project_id, new_project_name, new_project_number)
    resource_handler.import_gcp_project(project=new_gcp_project)
    resource_handler.create_location_specific_env(new_gcp_project.id)
    set_progress("Imported the new project, done!")



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

    return [(resource_handler.id, "{resource_handler}".format(resource_handler=resource_handler))
            for resource_handler in resource_handlers]


def generate_options_for_billing_name(control_value=None, **kwargs):
    if not control_value:
        return []
    resource_handler = GCPHandler.objects.get(id=control_value)
    credentials = Credentials(**json.loads(resource_handler.gcp_api_credentials))
    service = discovery.build('cloudbilling', 'v1', credentials=credentials, cache_discovery=False)
    request = service.billingAccounts().list()
    billiing_list = request.execute()["billingAccounts"]
    return [(b["name"], b["displayName"]) for b in billiing_list]