"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import requests
import time 
from resources.models import Resource, ResourceType
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler
from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

API_VERSION = "2018-06-01"


def get_or_create_custom_fields():
    
    CustomField.objects.get_or_create(
        name='azure_resource_type',
        defaults={
            'label': 'Resource Type', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name='azure_resource_status',
        defaults={
            'label': 'Resource Status', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers': True
        }
    )


def get_or_create_resource_type():
    # get or create resource type
    rt, created = ResourceType.objects.get_or_create(
        name="data_factory_pipeline",
        defaults={"label": "Data Factory Pipeline rerun type", "icon": "far fa-file"}
    )

    # get or create pipeline custom fields
    get_or_create_custom_fields()

    return rt
    

def generate_options_for_azure_resource_status(server=None, **kwargs):
    resource = kwargs.get('resource', None)
    if resource is None:
        return []
        
    return[(f"Failed/{resource.id}","Failed"), (f"Succeeded/{resource.id}","Succeeded")]
    

def generate_options_for_rerun_pipeline(server=None, control_value=None, **kwargs,):
    """
    Generate rerun pipeline options
    Dependency - azure_resource_status
    """    
    options = []

    if not control_value:
        return options
        
    control_value = control_value.split('/')
 
    sub_resources = Resource.objects.filter(parent_resource__id=control_value[1], lifecycle="ACTIVE")

    for sub_resource in sub_resources:
        
        # fetching custom field values as dictionary
        resource_cf_dict = sub_resource.get_cf_values_as_dict()
        
        #verifying azure resource status 
        if "run_id" in resource_cf_dict and resource_cf_dict["run_id"] != "" and "azure_resource_status" in resource_cf_dict \
            and resource_cf_dict['azure_resource_status'] == control_value[0]:
            
            options.append((sub_resource.id,sub_resource.name))
            
    return sorted(options, key=lambda tup: tup[1].lower())   


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


def create_pipeline_cb_subresource(fs_obj, resource, resource_type, job):
    """
    Create pipeline cb sub resource
    params: resource : resource object
    params: resource : resource_type object
    params: fs_obj : fetched pipelineruns object for updated status 
    """
    # create pipeline as a sub resource of blueprint
    res = Resource.objects.create(
        group=resource.group, parent_resource=resource, resource_type=resource_type, name=fs_obj.get("pipelineName",""),
        blueprint=resource.blueprint, lifecycle="ACTIVE", owner=job.owner)

    # assign customfield attribute
    res.azure_resource_status = fs_obj.get("status")
    res.azure_resource_type = "Re-Run Pipeline"
    res.save()

    logger.info(f'Sub Resource {res} created successfully.')


def create_pipeline_rerun(pipeline, resource, resource_type, job):
    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)

    # get azure resource header for data factory client api
    headers = _get_rest_api_header(azure_rh)

    # custom field of pipeline object to fetch run id
    reference_pipeline_cf = pipeline.get_cf_values_as_dict()

    base_url = f"https://management.azure.com/"

    factory_endpoint_path = f"subscriptions/{azure_rh.serviceaccount}/resourceGroups/{resource.resource_group}/providers/Microsoft.DataFactory/factories/"

    pipeline_endpoint_path = f"{resource.data_factory_name}/pipelines/{pipeline}/createRun?"

    payload = {
        "api-version": API_VERSION,
        "referencePipelineRunId": reference_pipeline_cf['run_id'], # reference run id which is run id of run pipeline
        "isRecovery": True  #referenced pipeline run and the new run will be grouped under the same groupId.
    }

    api_url = f"{base_url}{factory_endpoint_path}{pipeline_endpoint_path}"
    
    # rerun pipeline
    rr_rsp = requests.request("POST", api_url, headers=headers, params=payload)

    if rr_rsp.status_code not in range(200, 299):
        raise RuntimeError(f"Unexpected error occurred: {rr_rsp.json()}")

    logger.info(f"pipeline Re-Run {rr_rsp.json()} created successfully!")
    
    #runid of corresponding pipeline to fetch updated status 
    fs_runid=rr_rsp.json().get("runId")
    
    time.sleep(30)

    params = {
        "api-version": API_VERSION
    }

    api_url = f"{base_url}{factory_endpoint_path}{resource.data_factory_name}/pipelineruns/{fs_runid}?"

    #fetching updated resource status of rerun pipeline 
    fs_rsp = requests.request("GET",api_url, headers=headers, params=params)
    
    #fetched pipelineruns object
    fs_obj = fs_rsp.json()

    # create rerun pipeline cb sub resource
    create_pipeline_cb_subresource(fs_obj, resource, resource_type, job)
    

def run(job, resource, **kwargs):
    set_progress(f"Starting Provision of {resource} rerun pipeline.")
    logger.info(f"Starting Provision of {resource} rerun pipeline.")
    
    resource_type = get_or_create_resource_type()
    
    resource_status = "{{azure_resource_status}}"
    rerun_pipeline_id = "{{rerun_pipeline}}"

    # get pipeline model object
    pipeline = Resource.objects.get(id=rerun_pipeline_id)

    logger.info(f"pipeline : {pipeline}")

    # create data factory pipeline rerun
    create_pipeline_rerun(pipeline, resource, resource_type, job)

    return "SUCCESS", "Data factory pipeline rerun successfully", ""
