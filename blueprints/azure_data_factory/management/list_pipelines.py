"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
from azure.mgmt.datafactory import DataFactoryManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
from resources.models import Resource, ResourceType
from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def get_or_create_custom_fields():
    
    CustomField.objects.get_or_create(
        name='azure_pipeline_id', 
        defaults={
            'label': 'Data Factory Pipeline ID', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': False
        }
    )
    
    CustomField.objects.get_or_create(
        name='activity_name', 
        defaults={
            'label': 'Activity Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name='dataset_source_name', 
        defaults={
            'label': 'Dataset Source Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name='dataset_sink_name', 
        defaults={
            'label': 'Dataset Sink Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers':True
        }
    )
    
    
def get_or_create_resource_type():
    
    # get or create resource type
    rt, _ = ResourceType.objects.get_or_create(
        name="data_factory_pipeline",
        defaults={"label": "Data Factory Pipeline", "icon": "far fa-file"}
    )
    
    # get or create pipeline custom fields
    get_or_create_custom_fields()
    
    return rt
    
    
def _get_data_factory_client(rh):

    # initialize data factory client 
    adf_client = DataFactoryManagementClient(rh.get_api_wrapper().credentials, rh.serviceaccount)
    
    return adf_client
    

def create_pipeline_cb_subresource(resource, resource_type, azure_pipeline):
    """
    Create pipeline
    params: resource : resource object
    params: resource : resource_type object
    params: azure_pipeline : azure pipeline object 
    """
    
    # create pipeline as a sub resource of blueprint
    res = Resource.objects.create(group=resource.group, parent_resource=resource, resource_type=resource_type, name=azure_pipeline.name, 
                        blueprint=resource.blueprint, lifecycle="ACTIVE")
    
    res.azure_pipeline_id = azure_pipeline.id

    if azure_pipeline.activities:
        res.activity_name = azure_pipeline.activities[0].name
    
        if azure_pipeline.activities[0].inputs:
            res.dataset_source_name = azure_pipeline.activities[0].inputs[0].reference_name
        
        if azure_pipeline.activities[0].outputs:
            res.dataset_sink_name = azure_pipeline.activities[0].outputs[0].reference_name
        
    res.save()
    
    logger.debug(f'Sub Reousce {res} created successfully.')
                
    
def list_data_factory_pipelines(adf_client, rg_name, df_name, sub_resources, resource_type, resource):
    """
    Fetch the data factory pipelines and create it on cb server if it does not exist
    Return list
    """
    discovered_objects = []
    
    # fetch all data factory pipelines
    for pipeline in adf_client.pipelines.list_by_factory(resource_group_name=rg_name, factory_name=df_name): 
    
        discovered_objects.append(
            {
                'name': pipeline.name,
                'type': pipeline.activities[0].type,
                'id': pipeline.id,
            })
        
        # search pipeline name in cb resource
        res = sub_resources.filter(name=pipeline.name).first()
        
        if not res:
            set_progress("Found new data factory pipelinet '{0}', creating sub-resource...".format(pipeline.name))
            
            # create pipeline cb resource
            create_pipeline_cb_subresource(resource, resource_type, pipeline)
        
    return discovered_objects


def run(job, resource, **kwargs):
    set_progress(f"Connecting reousce {resource} to azure data factory workspace")
    logger.debug(f'Connecting reousce {resource} to azure data factory workspace.')
    
    # get or create resource type object
    rt = get_or_create_resource_type()
    
    # get all sub resource objects
    sub_resources = Resource.objects.filter(parent_resource=resource, resource_type=rt, lifecycle="ACTIVE")
    
    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)
    
    # get data factory client object
    adf_client = _get_data_factory_client(azure_rh)
    
    # fetch all data factory pipelines
    pipelines = list_data_factory_pipelines(adf_client, resource.resource_group, resource.data_factory_name, sub_resources, rt, resource)
    
    logger.debug(f'Data factory pipelines:  {pipelines}')
    
    set_progress(pipelines)
    
    return "SUCCESS", "Data factory pipelines synced successfully", ""