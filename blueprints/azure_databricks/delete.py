"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import sys
import time
from resourcehandlers.azure_arm.models import AzureARMHandler
from common.methods import set_progress
from utilities.logger import ThreadLogger
from msrestazure.azure_exceptions import CloudError

logger = ThreadLogger(__name__)


def get_api_version(id_value):
    return '2018-04-01'
 
def delete_resource(resource_client, api_version, resource_id, wrapper):
    """
    Delete databricks workspace
    """
    try:
        response = resource_client.resources.delete_by_id(resource_id, api_version)
        # Need to wait for each delete to complete in case there are
        # resources dependent on others (VM disks, etc.)
        wrapper._wait_on_operation(response)
    except:
        return False
    
    return True


def verify_resource(resource_client, resource_id, api_version, not_verified=0):
    """
    Verify databricks workspace
    """
    try:
        resource_client.resources.get_by_id(resource_id, api_version)
    except CloudError as ce:
        try:
            reason = ce.error.error
        except:
            reason = ce.error.response.reason
            
        if reason == 'ResourceNotFound' or reason == 'DeploymentNotFound' or \
                reason == 'Not Found':
            logger.info(f'resource_id: {resource_id} could not be '
                        f'found, it may have already been deleted. '
                        f'Continuing')
        else:
            logger.warn(f'Could not get resource id: {resource_id}'
                        f'Error: {ce.message}')
        
        if not_verified > 2:
            return False
        
        not_verified+=1
        time.sleep(10)
        
        # retry to verify databricks workspace
        verify_resource(resource_client, resource_id, api_version, not_verified)
        
    return True
                            
def run(job, *args, **kwargs):
    # get resource object
    resource = job.resource_set.first()
    
    if resource is None:
        set_progress("Resource was not found")
        return "SUCCESS", "Resource was not found", ""
    
    set_progress(f"Databricks Delete plugin running for resource: {resource}")
    logger.info(f"Databricks Delete plugin running for resource: {resource.name}")
    
    
    try:
        azure_rh_id = resource.azure_rh_id
        if azure_rh_id is None:
            raise Exception(f'RH ID not found.')
    except:
        msg = "No RH ID set on the blueprint, continuing"
        set_progress(msg)
        return "SUCCESS", msg, ""

    # Instantiate Azure Resource Client
    rh: AzureARMHandler = AzureARMHandler.objects.get(id=azure_rh_id)
    wrapper = rh.get_api_wrapper()

    # get resource client
    resource_client = wrapper.resource_client

    # get resource dict object
    resource_dict = resource.get_cf_values_as_dict()
    
    resource_id = resource_dict['azure_resource_id']
    
    # get api version
    api_version = get_api_version(resource_id)

    attempts = 0
    is_deleted = False
    

    while attempts < 2:
        
        # verified azure resource id
        if not verify_resource(resource_client, resource_id, api_version):
            return "WARNING", "Resource not found, it may have already been deleted", ""
        

        set_progress(f'Deleting Azure Resource with ID: '
                                f'{resource_id}, using api_version: '
                                f'{api_version}')
        
        # delete resource from azure portal
        is_deleted = delete_resource(resource_client, api_version, resource_id, wrapper)

        if is_deleted:
            break
            
        attempts+=1
            
 
    if not is_deleted:
        logger.error(f'These ID failed deletion: {resource_id}')
        return "WARNING", "Some resources failed deletion", ""
    

    return "SUCCESS", "Resources deleted successfully", ""