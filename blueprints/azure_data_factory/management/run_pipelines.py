"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import time
from resources.models import Resource,ResourceType
from common.methods import set_progress
from azure.mgmt.datafactory import DataFactoryManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler

from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields():

    CustomField.objects.get_or_create(
        name='run_pipeline', 
        defaults={
            'label': 'Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True
        }
    )
    
    CustomField.objects.get_or_create(
        name='azure_resource_type', 
        defaults={
            'label': 'Resource Type', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True,'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name='azure_resource_status', 
        defaults={
            'label': 'Resource Status', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True,'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name='run_id', 
        defaults={
            'label': 'Run id', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True
        }
    )
    
    
def get_or_create_resource_type():
    
    # get or create resource type
    rt, created = ResourceType.objects.get_or_create(
        name="data_factory_pipeline",
        defaults={"label": "Data Factory Pipeline", "icon": "far fa-file"}
    )
        
    # get or create pipeline custom fields
    get_or_create_custom_fields()

    return rt
    
    
def generate_options_for_run_pipeline(server=None, **kwargs):
    resource = kwargs.get('resource', None)
    options = [("", "------Select Pipeline-------")]

    if resource is None:
        return options
        
    # get all sub resources
    sub_resources = Resource.objects.filter(parent_resource=resource, lifecycle="ACTIVE")
    
    for sub_resource in sub_resources:
        # fetching custom field values as dictionary
        resource_cf_dict = sub_resource.get_cf_values_as_dict()
        
        # check run_id to identify resource of ony run pipeline
        if "run_id" in resource_cf_dict and resource_cf_dict["run_id"] != "" or "re_run_id" in resource_cf_dict and resource_cf_dict['re_run_id'] != "":
            continue
        
        options.append((sub_resource.name, sub_resource.name))
   
    return sorted(options, key=lambda tup: tup[1].lower())
    

def _get_data_factory_client(rh):
    """
    params: rh : azure resource handler object
    """
    # initialize data factory client 
    adf_client = DataFactoryManagementClient(rh.get_api_wrapper().credentials, rh.serviceaccount)
   
    return adf_client
    

def create_pipeline_cb_subresource(resource,rt,pipeline_run, job):
    """
    Create pipeline cb sub resource
    params: resource : resource object
    params: resource : resource_type object
    params: azure_pipeline : azure pipeline object 
    """
    
    # create pipeline as a sub resource of blueprint
    res = Resource.objects.create(
            group=resource.group, parent_resource=resource, resource_type=rt, name=pipeline_run.pipeline_name, blueprint=resource.blueprint, lifecycle="ACTIVE", owner=job.owner)
            
    res.run_pipeline = pipeline_run.pipeline_name
    res.azure_resource_status = pipeline_run.status
    res.azure_resource_type = "Run Pipeline"
    res.run_id=pipeline_run.run_id
    res.save()

    logger.info(f'Sub Reousce {res} created successfully.')   


def create_pipeline_run(pipeline_objects, resource, rt, job):
    
    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)
    
    # get data factory client object
    adf_client = _get_data_factory_client(azure_rh)
    
    run_response = adf_client.pipelines.create_run(resource.resource_group, resource.data_factory_name, pipeline_objects, parameters={})
    
    time.sleep(30)
    
    pipeline_run = adf_client.pipeline_runs.get(resource.resource_group,  resource.data_factory_name, run_response.run_id)

    create_pipeline_cb_subresource(resource, rt, pipeline_run, job)
    

def run(job, resource, **kwargs):
    set_progress(f"Starting Provision of {resource} run piplines.")
    logger.info(f"Starting Provision of {resource} run piplines.")
    
    # get or create resource type object
    rt = get_or_create_resource_type()

    run_pipeline = "{{run_pipeline}}"

    logger.info(f"run pipeline : {run_pipeline}")

    # create data factory pipeline run
    create_pipeline_run(run_pipeline, resource, rt, job)
    
    return "SUCCESS", "Data factory pipeline started successfully", ""