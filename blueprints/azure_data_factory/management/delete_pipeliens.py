"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import ast
from common.methods import set_progress
from azure.mgmt.datafactory import DataFactoryManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler

from resources.models import Resource
from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields():
    
    CustomField.objects.get_or_create(
        name='delete_pipelines', 
        defaults={
            'label': 'Delete Pipelines', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'allow_multiple': True
        }
    )
    
def generate_options_for_delete_pipelines(server=None, **kwargs):
    resource = kwargs.get('resource', None)
    options = [("", "------Select Pipelines-------")]

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
        
        options.append((sub_resource.id, sub_resource.name))
    
    return sorted(options, key=lambda tup: tup[1].lower())

def _get_data_factory_client(rh):
    """
    params: rh : azure resource handler object
    """
    # initialize data factory client 
    adf_client = DataFactoryManagementClient(rh.get_api_wrapper().credentials, rh.serviceaccount)
    
    return adf_client
    
def delete_pipelines(pipeline_objects, resource):
    
    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)
    
    # get data factory client object
    adf_client = _get_data_factory_client(azure_rh)
    
    for pipeline in Resource.objects.filter(id__in=pipeline_objects, parent_resource=resource, lifecycle="ACTIVE"):
        
        # delete pipeline from azure portal
        adf_client.pipelines.delete(pipeline_name=pipeline.name, factory_name=resource.data_factory_name, 
                                        resource_group_name=resource.resource_group)
        
        if pipeline.dataset_source_name != "":
            try:
                # delete datasets source from azure portal
                adf_client.datasets.delete(dataset_name=pipeline.dataset_source_name, factory_name=resource.data_factory_name, 
                                                resource_group_name=resource.resource_group)
            except Exception as err:
                logger.info(err)
        
        if pipeline.dataset_sink_name != "":
            try:
                # delete datasets sink from azure portal
                adf_client.datasets.delete(dataset_name=pipeline.dataset_sink_name, factory_name=resource.data_factory_name, 
                                            resource_group_name=resource.resource_group)
            except Exception as err:
                logger.info(err)
        
        # delete from cb server
        pipeline.delete()
        
def run(job, resource, **kwargs):
    set_progress(f"Starting Provision of {resource} delete piplines.")
    logger.info(f"Starting Provision of {resource} delete piplines.")
    
    try:
        # Safely evaluate an expression
        pipeline_objects = ast.literal_eval("{{delete_pipelines}}")
    except Exception as err:
        raise RuntimeError(err)
    
    if not isinstance(pipeline_objects, list):
        pipeline_objects = [pipeline_objects]
        
    # get or create custom fields
    get_or_create_custom_fields()
    
    logger.info(f"pipeline objects : {pipeline_objects}")
    
    # delete data factory pipelines
    delete_pipelines(pipeline_objects, resource)
    
    return "SUCCESS", "Data factory pipelines deleted successfully", ""