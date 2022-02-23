"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import requests
import json
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import BlobSource, BlobSink, DatasetReference, CopyActivity, PipelineResource
from azure.storage.common.models import AccountPermissions, ResourceTypes
from azure.storage.blob.baseblobservice import BaseBlobService
from datetime import datetime, timedelta

from resourcehandlers.azure_arm.models import AzureARMHandler
from resources.models import Resource, ResourceType
from infrastructure.models import CustomField
from utilities.logger import ThreadLogger
from common.methods import set_progress

logger = ThreadLogger(__name__)

API_VERSION = "2018-06-01"

"""
Azure DevOps Services REST API 7.1 => create github pipeline and perform other operations
https://docs.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/create?view=azure-devops-rest-7.1
"""


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
            'required': True, 'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name='dataset_source_name',
        defaults={
            'label': 'Dataset Source Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name='dataset_sink_name',
        defaults={
            'label': 'Dataset Sink Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, 'show_on_servers': True
        }
    )

    CustomField.objects.get_or_create(
        name='pipeline_name',
        defaults={
            'label': 'Pipeline Name', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True
        }
    )
    
    CustomField.objects.get_or_create(
        name='source_storage',
        defaults={
            'label': 'Source Storage', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, "placeholder":"---Select Source Storage----"
        }
    )
    
    CustomField.objects.get_or_create(
        name='dataset_source_container',
        defaults={
            'label': 'Dataset Source Container', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, "placeholder":"---Select Source Container----"
        }
    )
    
    CustomField.objects.get_or_create(
        name='source_container_file',
        defaults={
            'label': 'Dataset Source Container File', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, "placeholder":"---Select Source Container File----"
        }
    )
    
    CustomField.objects.get_or_create(
        name='dataset_source_container',
        defaults={
            'label': 'Dataset Sink Container', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, "placeholder":"---Select Sink Container----"
        }
    )
    
    CustomField.objects.get_or_create(
        name='sink_storage',
        defaults={
            'label': 'Sink Storage', 'type': 'STR',
            'description': 'Used by the Azure data factory blueprints',
            'required': True, "placeholder":"---Select Sink Storage----"
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


def get_rest_api_header(rh):
    """
    params: rh : azure resource handler object
    """
    access_token = rh.get_api_wrapper().credentials.token['access_token']

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    return headers


def get_data_factory_client(rh):

    # initialize data factory client
    adf_client = DataFactoryManagementClient(
        rh.get_api_wrapper().credentials, rh.serviceaccount)

    return adf_client


def sort_dropdown_options(options, placeholder=None):
    """
    Sort dropdown options 
    """
    # sort options
    options = sorted(options, key=lambda tup: tup[1].lower())
    
    if placeholder is not None:
        options.insert(0, placeholder)
        
        options = {"options": options, "override": True}
        
    return options


def get_azure_storage_accounts(resource, options):
    if resource is None:
        return options

    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)

    for storage_acc in azure_rh.get_api_wrapper().storage_client.client.storage_accounts.list():
        reource_group = storage_acc.id.split("/")[4]
        options.append(
            (f'{azure_rh.id}/{reource_group}/{storage_acc.name}', storage_acc.name))

    return options


def generate_options_for_source_storage(server=None, **kwargs):
    """
    Generate options for dataset source storage
    """

    resource = kwargs.get('resource', None)
    options = []
    return sort_dropdown_options(get_azure_storage_accounts(resource, options), ("", "-------Select Source Storage-------"))


def generate_options_for_sink_storage(server=None, **kwargs):
    """
    Generate options for dataset sink storage
    """

    resource = kwargs.get('resource', None)
    options = []
    return sort_dropdown_options(get_azure_storage_accounts(resource, options), ("", "-------Select Sink Storage-------"))


def generate_options_for_dataset_source_container(server=None, control_value=None, **kwargs):
    """
    Generate dataset source container options
    It's depend on source storage
    """
    options = []

    if control_value is None or control_value == '':
        # options.append(("", "-------First, Select Source Storage-------"))
        return options

    control_value = control_value.split("/")

    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=control_value[0])

    # fetch storage containers
    for container in azure_rh.get_api_wrapper().storage_client.client.blob_containers.list(control_value[1], control_value[2]):
        options.append(
            (f"{azure_rh.id}/{control_value[1]}/{control_value[2]}/{container.name}", container.name))

    return sort_dropdown_options(options, ("", "-------Select Source Container-------"))


def generate_options_for_source_container_file(server=None, control_value=None, **kwargs):
    """
    Generate dataset source container file options
    It's depend on source storage container
    """
    
    options = []

    if control_value is None or control_value == "":
        # options.append(("", "-------First, Select Source Container-------"))
        return options

    control_value = control_value.split("/")
    account_key = ""

    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=control_value[0])

    # get storage account key
    for key_obj in azure_rh.get_api_wrapper().storage_client.client.storage_accounts.list_keys(control_value[1], control_value[2]).keys:
        account_key = key_obj.value
        break

    if account_key == "":
        raise RuntimeError("Not found storage account key.")

    # initialize account permission object
    permission = AccountPermissions(read=True, write=True, delete=False, list=True,
                                    add=False, create=True, update=False, process=False, _str=None)

    # initialize blob service object
    bbs = BaseBlobService(
        account_name=control_value[2], account_key=account_key)

    # initialize resource type
    resource_types = ResourceTypes(service=True, container=True, object=True)

    # get sas blob service token
    sas_token = bbs.generate_account_shared_access_signature(resource_types=resource_types, permission=permission,
                                                             expiry=datetime.utcnow() + timedelta(minutes=30))

    # fetch all container blobs
    blobs = BaseBlobService(
        account_name=control_value[2], sas_token=sas_token).list_blobs(control_value[3])

    for blob in blobs:
        options.append((blob.name, blob.name))

    return sort_dropdown_options(options, ("", "-------Select Source Container File-------"))


def generate_options_for_dataset_sink_container(server=None, control_value=None, **kwargs):
    """
    Generate dataset sink container options
    It's depend on sink storage
    """
    options = []

    if control_value is None or control_value == '':
        # options.append(("", "-------First, Select Sink Storage-------"))
        return options

    control_value = control_value.split("/")

    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=control_value[0])

    for container in azure_rh.get_api_wrapper().storage_client.client.blob_containers.list(control_value[1], control_value[2]):
        options.append((container.name, container.name))

    return sort_dropdown_options(options, ("", "-------Select Sink Container-------"))


def create_linked_service_resource(headers, rh, resource_id, ls_name, resource_group, st_account_name):
    """
    Create or update linked service resource
    params: azure_resource_id : azure resource id
    params: ls_name :Linked service name
    params: st_account_name :Storage account name
    params: st_account_key :Storage account key
    params: headers : request api header
    """
    set_progress(f"Starting Provision of {ls_name} linked service.")
    logger.info(f"Starting Provision of {ls_name} linked service.")

    st_account_key = ""

    # get storage account key
    for key_obj in rh.get_api_wrapper().storage_client.client.storage_accounts.list_keys(resource_group, st_account_name).keys:
        st_account_key = key_obj.value
        break

    if st_account_key == "":
        raise RuntimeError("Not found storage account key.")

    # IMPORTANT: specify the name and key of your Azure Storage account.
    storage_string = f'DefaultEndpointsProtocol=https;AccountName={st_account_name};AccountKey={st_account_key};EndpointSuffix=core.windows.net'

    ls_payload = {
        "name": ls_name,
        "properties": {
            "annotations": [],
            "type": "AzureBlobStorage",
            "typeProperties": {"connectionString": storage_string}
        }
    }

    api_url = f'https://management.azure.com{resource_id}/linkedservices/{ls_name}?api-version={API_VERSION}'

    # create linked service
    ls = requests.request("PUT", api_url, headers=headers,
                          data=json.dumps(ls_payload))

    if ls.status_code != 200:
        raise RuntimeError(f"Unexpected error occurred: {ls.json()}")

    logger.info(f"Linked service {ls.json()} created or updated successfully!")


def create_datasets(headers, resource_id, dataset_source_name, dataset_sink_name, ls_name, dataset_source_container, dataset_sink_container, blob_filename):
    """
    Create or update pipeline datasets
    params: headers : request header dict
    params: resource_id : azure resource id
    params: dataset_source_name : source dataset name
    params: dataset_sink_name : sink dataset name
    params: dataset_source_container : source folder name # '<container>/<folder path>'
    params: dataset_sink_container : sink folder name # '<container>/<folder path>'
    params: blob_filename : source bolb file name # '24dectest.txt'  # '<file name>'
    params: ls_name : Linked service name
    """
    set_progress(
        f"Starting Provision of {dataset_source_name} and {dataset_sink_name} dataset in and out.")
    logger.info(
        f"Starting Provision of {dataset_source_name} and {dataset_sink_name} dataset in and ou.")

    # dataset input payload
    ds_payload = {
        "properties": {
            "type": "AzureBlob",
            "typeProperties": {
                "folderPath": f'{dataset_source_container}/',
                "fileName": blob_filename,
                "compression": {
                    "type": "BZip2",
                    "level": "Optimal"
                }
            },
            "description": "Example description",
            "linkedServiceName": {
                "referenceName": ls_name,
                "type": "LinkedServiceReference"
            }
        }
    }

    api_url = f'https://management.azure.com{resource_id}/datasets/{dataset_source_name}?api-version={API_VERSION}'

    # create input dataset
    dsIn = requests.request(
        "PUT", api_url, headers=headers, data=json.dumps(ds_payload))

    if dsIn.status_code != 200:
        raise RuntimeError(f"Unexpected error occurred: {dsIn.json()}")

    logger.info(f"Dataset in {dsIn.json()} created successfully!")

    # set dataset sink container
    ds_payload['properties']['typeProperties']['folderPath'] = dataset_sink_container

    if "fileName" in ds_payload['properties']['typeProperties']:
        del ds_payload['properties']['typeProperties']['fileName']

    api_url = f'https://management.azure.com{resource_id}/datasets/{dataset_sink_name}?api-version={API_VERSION}'

    # create output dataset
    dsOut = requests.request(
        "PUT", api_url, headers=headers, data=json.dumps(ds_payload))

    if dsOut.status_code != 200:
        raise RuntimeError(f"Unexpected error occurred: {dsOut.json()}")

    logger.debug(f"Dataset out {dsOut.json()} created successfully!")


def azure_create_data_factory_pipeline(adf_client, act_name, dataset_source_name, dataset_sink_name, pipeline_name, rg_name, df_name):
    """
    Create or update data factory pipeline with copy activity on azure portal
    params: adf_client : Data factory client object
    params: act_name : Copy activity name
    params: dataset_source_name : input dataset name
    params: dataset_sink_name : output dataset name
    params: rg_name : Resource group name
    params: df_name : Data factory name
    params: pipeline_name : Pipeline name
    """
    set_progress(
        f"Starting Provision of {pipeline_name} pipeline with activity.")
    logger.info(
        f"Starting Provision of {pipeline_name} pipeline with activity.")

    blob_source = BlobSource()
    blob_sink = BlobSink()
    dsin_ref = DatasetReference(reference_name=dataset_source_name)
    dsOut_ref = DatasetReference(reference_name=dataset_sink_name)

    # create copy activity object
    copy_activity = CopyActivity(name=act_name, inputs=[dsin_ref], outputs=[
        dsOut_ref], source=blob_source, sink=blob_sink)

    # Create a pipeline with the copy activity
    # Note1: To pass parameters to the pipeline, add them to the json string params_for_pipeline shown below in the format { "ParameterName1" : "ParameterValue1" } for each of the parameters needed in the pipeline.
    # Note2: To pass parameters to a dataflow, create a pipeline parameter to hold the parameter name/value, and then consume the pipeline parameter in the dataflow parameter in the format @pipeline().parameters.parametername.

    params_for_pipeline = {}
    p_obj = PipelineResource(
        activities=[copy_activity], parameters=params_for_pipeline)

    # create pipeline
    azurePipelineObj = adf_client.pipelines.create_or_update(
        rg_name, df_name, pipeline_name, p_obj)

    logger.info(f"Pipeline {azurePipelineObj} deployed successfully!")

    return azurePipelineObj


def create_pipeline_cb_subresource(resource, resource_type, azure_pipeline, job):
    """
    Create pipeline cb sub resource
    params: resource : resource object
    params: resource : resource_type object
    params: azure_pipeline : azure pipeline object
    params: job : request job object

    """

    # create pipeline as a sub resource of blueprint
    res = Resource.objects.create(group=resource.group, parent_resource=resource, resource_type=resource_type, name=azure_pipeline.name,
                                  blueprint=resource.blueprint, lifecycle="ACTIVE", owner=job.owner)

    res.azure_pipeline_id = azure_pipeline.id

    if azure_pipeline.activities:
        # set custom fields value

        res.activity_name = azure_pipeline.activities[0].name

        if azure_pipeline.activities[0].inputs:
            res.dataset_source_name = azure_pipeline.activities[0].inputs[0].reference_name

        if azure_pipeline.activities[0].outputs:
            res.dataset_sink_name = azure_pipeline.activities[0].outputs[0].reference_name

    res.save()

    logger.info(f'Sub Reousce {res} created successfully.')


def run(job, resource, **kwargs):
    set_progress(f"Starting Provision of {resource} resource pipline.")
    logger.debug(f"Starting Provision of {resource} resource pipline.")
    
    # get or create resource type and custom fields
    resource_type = get_or_create_resource_type()
    
    pipeline_name = '{{pipeline_name}}'.replace(" ", "_")
    act_name = '{{activity_name}}'.replace(" ", "_")
    ls_name = 'BlobLinkedService'
    source_storage = "{{source_storage}}".split("/") # dataset source storage, it's drop down field
    dataset_source_container = '{{dataset_source_container}}'.split("/")[-1] # dataset source container, it's drop down field and depend on source storage
    source_container_file = '{{source_container_file}}' # dataset source container file, it's drop down field and depend on source storage container
    sink_storage = "{{sink_storage}}" # dataset sink storage, it's drop down field
    dataset_sink_container = '{{dataset_sink_container}}' # dataset source container, it's drop down field and depend on sink storage 
    dataset_source_name = f'ds_source_{dataset_source_container}_{job.id}' # dataset source name
    dataset_sink_name = f'ds_sink_{dataset_sink_container}_{job.id}' # dataset sink name

    # get azure resource handler object
    azure_rh = AzureARMHandler.objects.get(id=resource.azure_rh_id)

    # get data factory client object
    headers = get_rest_api_header(azure_rh)

    # create linked service
    create_linked_service_resource(
        headers, azure_rh, resource.azure_resource_id, ls_name, source_storage[1], source_storage[2])

    # create in/out dataset
    create_datasets(headers, resource.azure_resource_id, dataset_source_name, dataset_sink_name, ls_name,
                    dataset_source_container, dataset_sink_container, source_container_file)

    # create pipeline with copy activity on azure portal
    azurePipelineObj = azure_create_data_factory_pipeline(get_data_factory_client(azure_rh), act_name, dataset_source_name, dataset_sink_name,
                                                          pipeline_name, resource.resource_group, resource.data_factory_name)

    # create pipeline cb sub resource
    create_pipeline_cb_subresource(resource, resource_type, azurePipelineObj, job)

    return "SUCCESS", "Data factory pipeline created successfully", ""