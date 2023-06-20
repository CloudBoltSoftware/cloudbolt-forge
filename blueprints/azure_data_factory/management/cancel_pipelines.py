"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import requests
from resources.models import Resource
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler

from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

API_VERSION = "2018-06-01"


def generate_options_for_azure_resource_status(server=None, **kwargs):
    """
    generate_options_for_azure_resource_status
    """
    resource = kwargs.get('resource', None)
    
    if resource is None:
        return []
        
    return[(f"InProgress/{resource.id}","InProgress"),(f"Queued/{resource.id}","Queued")]


def generate_options_for_cancel_pipeline(server=None, control_value=None, **kwargs):
    """
    Generate cancel pipeline options
    Dependency - azure_resource_status
    """    
    options = []

    if not control_value:
        return options
        
    control_value = control_value.split('/')

    sub_resources = Resource.objects.filter(parent_resource_id=control_value[1],lifecycle="ACTIVE")

    for sub_resource in sub_resources:
        
        reference_pipeline_cf = sub_resource.get_cf_values_as_dict()
        
        if "azure_resource_status" in reference_pipeline_cf and  reference_pipeline_cf["azure_resource_status"] ==control_value[0]:
            
            options.append((sub_resource.id,sub_resource.name))

    return options


def _get_rest_api_header(azure_rh):
    """
    params: azure_rh : azure resource handler object
    """
    access_token = azure_rh.get_api_wrapper().credentials.token['access_token']

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    return headers


def create_pipeline_cancel(pipeline_object, resource):
    
    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)

    # get azure resource header for data factory client api
    headers = _get_rest_api_header(azure_rh)

    # custom field of pipeline object to fetch run id
    reference_pipeline_cf = pipeline_object.get_cf_values_as_dict()
    
    # reference run id which is run id of run pipeline
    reference_pipeline_run_id = reference_pipeline_cf.get("run_id",None)

    # If true, cancel all the Child pipelines that are triggered by the current pipeline.
    is_recursive = True
    
    base_url = f"https://management.azure.com/"

    factory_endpoint_path = f"subscriptions/{azure_rh.serviceaccount}/resourceGroups/{resource.resource_group}/providers/Microsoft.DataFactory/factories/"

    pipeline_endpoint_path = f"{resource.data_factory_name}/pipelineruns/{reference_pipeline_run_id}/cancel?"

    params = {
        "api-version": API_VERSION,
        "isRecursive": is_recursive
    }   
    
    api_url = f"{base_url}{factory_endpoint_path}{pipeline_endpoint_path}"

    #cancel pipeline response
    cr = requests.request("POST", api_url, headers=headers, params=params)  
    
    #pipeline already succeeded while cancel api is in progress 
    if cr.status_code not in range(200, 299):
        
        cancel_message = cr.json()["error"]["message"]
        pipeline_object.azure_resource_status = "Succeeded"
        
    else:
        cancel_message ="Pipeline Cancelled Successfully"
        pipeline_object.azure_resource_status = "Cancelled"
        
    pipeline_object.save()   
        
    logger.info(f"pipeline cancel {pipeline_object} cancelled successfully!")
    
    return cancel_message


def run(job, resource, **kwargs):
    set_progress(f"Starting Provision of {resource} cancel pipeline.")
    logger.info(f"Starting Provision of {resource} cancel pipeline.")

    azure_resource_status = "{{azure_resource_status}}"
    cancel_pipeline_object = "{{cancel_pipeline}}"

    pipeline_object = Resource.objects.get(id=cancel_pipeline_object)

    logger.info(f"pipeline object : {cancel_pipeline_object}")

    # cancel and fetch response message of cancel pipeline
    msg = create_pipeline_cancel(pipeline_object, resource)

    return "SUCCESS", msg, ""
