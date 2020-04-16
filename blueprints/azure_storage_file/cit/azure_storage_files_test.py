import json
import logging
import re

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion, wait_for_job_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from orders.models import Order
import os

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 236

NEW_RESOURCE_NAME = "testsharecit-azure-test-file"

TEST_FILE_FILEPATH = "/opt/cloudbolt/"

TEST_FILE_NAME = "azure-test-file"

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-upk372yb/",
                "blueprint-items-arguments": {
                    "build-item-Azure Storage Files Blueprint": {
                        "parameters": {
                            "azure-storage-file-share-name-a678": "testsharecit",
                            "file-a678": "/opt/cloudbolt/azure-test-file",
                            "overwrite-files-a678": "False",
                            "storage-account-a678": "testcittstorage"
                        }
                    }
                },
                "resource-name": "testsharecit-azure-test-file",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

# END of BP specific variables

def generate_test_file(filepath, filename):
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    file_path_with_file_name = os.path.join(filepath,filename)
    
    if not os.path.exists(file_path_with_file_name):
        with open(file_path_with_file_name,'w') as file:
            file.write('this is a test file')

def get_id_from_href(order_href):
    split = order_href.split('/')
    return int(split[-2])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_id_from_href(order_href)
    set_progress("Current Running order: {}".format(order_id))
    result = wait_for_order_completion(client, order_id, 180, 10)
    order_object = Order.objects.filter(id=order_id).first()
    job_list = order_object.list_of_jobs()
    job_object = job_list[0]
    resource = job_object.get_resource()
    
    if not result == 0 and ( not resource or resource.lifecycle == 'PROVFAILED'):
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id))
    
    return resource

def test_delete_resource(client, resource):
    body = "{}"
    response = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))
    job_href = response['run-action-job']['self']['href']
    job_id = get_id_from_href(job_href)
    result = wait_for_job_completion(client, job_id, 180, 10)
    if not result == 0:
        raise CloudBoltException(
            "Resource deletion job {} did not succeed.".format(job_id))
    set_progress(
        "Resource deletion job {} completed successfully.".format(job_id))


def get_api_client():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return CloudBoltAPIClient(
        ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol)


def run(job, *args, **kwargs):
    bp = ServiceBlueprint.objects.get(id=BLUEPRINT)
    starting_resource_set = bp.resource_set.all()
    set_progress(
        "Running Continuous Infrastructure Test for blueprint {}".format(bp)
    )

    client = get_api_client()
    set_progress("### ORDERING BLUEPRINT TO TEST DELETING###", tasks_done=0, total_tasks=3)
    generate_test_file(TEST_FILE_FILEPATH, TEST_FILE_NAME)
    created_resource = test_order_blueprint(client)
    test_delete_resource(client, created_resource)
    resource_set_after_deleting = bp.resource_set.all()
    if not len(starting_resource_set) == len(resource_set_after_deleting):
        intersection == starting_resource_set & resource_set_after_deleting
        set_progress("Delete failed: resource set ending bigger than it started even after deleting added, here are the extra values: {}".format(intersection))




    # Order the BP
    set_progress("### ORDERING BLUEPRINT TO TEST DISCOVERY###", tasks_done=0, total_tasks=3)
    generate_test_file(TEST_FILE_FILEPATH, TEST_FILE_NAME)
    created_resource = test_order_blueprint(client)
    created_resource_name= created_resource.name
    created_resource_azure_storage_file_name = created_resource.azure_storage_file_name
    created_resource_azure_storage_file_share_name = created_resource.azure_storage_file_share_name
    created_resource_resource_group_name = created_resource.resource_group_name
    created_resource_azure_storage_account_name = created_resource.azure_storage_account_name
    created_resource_azure_account_key = created_resource.azure_account_key
    created_resource_azure_account_key_fallback = created_resource.azure_account_key_fallback

 
    set_progress(f"RESOURCE {created_resource}")
    rce = bp.resource_set.last()
    set_progress(f"LAST RESOURCE {rce}")
    # Delete the resource from the database only
    created_resource.delete()

    set_progress("active resources before sync: {}".format(bp.resource_set.filter(lifecycle='Active')))
    set_progress("provisioning resources before sync: {}".format(bp.resource_set.filter(lifecycle='Provisioning')))
    set_progress("all resources before sync: {}".format(bp.resource_set.all()))
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    set_progress("active resources after sync: {}".format(bp.resource_set.filter(lifecycle='Active')))
    set_progress("provisioning resources after sync: {}".format(bp.resource_set.filter(lifecycle='Provisioning')))
    set_progress("all resources after sync: {}".format(bp.resource_set.all()))
    discovered_resource = bp.resource_set.filter(
        name=NEW_RESOURCE_NAME, lifecycle='Active').first()
    
    if not discovered_resource:
        discovered_resource = bp.resource_set.filter(
            name=NEW_RESOURCE_NAME).first()

    set_progress('filtered set: {}'.format(bp.resource_set.filter(name=NEW_RESOURCE_NAME)))
    set_progress('discovered_resource: {}'.format(discovered_resource))
    set_progress('created_resource_name: {}'.format(created_resource_name))
    sync_failed = False
    failure_message = ''
    
    try:
        if not discovered_resource.name == created_resource_name:
            raise CloudBoltException('Sync failed: Discovered resource\'s name not the same as created resource, {} =/= {}'.format(discovered_resource.name, created_resource_name))

        if not discovered_resource.azure_storage_file_name == created_resource_azure_storage_file_name:
            raise CloudBoltException('Sync failed: Discovered resource\'s azure_storage_file_name not the same as created resource, {} =/= {}'.format(discovered_resource.azure_storage_file_name, created_resource_azure_storage_file_name))

        if not discovered_resource.azure_storage_file_share_name == created_resource_azure_storage_file_share_name:
            raise CloudBoltException('Sync failed: Discovered resource\'s azure_storage_file_share_name not the same as created resource, {} =/= {}'.format(discovered_resource.azure_storage_file_share_name, created_resource_azure_storage_file_share_name))
                                                                                
        if not discovered_resource.azure_storage_account_name == created_resource_azure_storage_account_name:
            raise CloudBoltException('Sync failed: Discovered resource\'s azure_storage_account_name not the same as created resource, {} =/= {}'.format(discovered_resource.azure_storage_account_name, created_resource_azure_storage_account_name))

        if not discovered_resource.azure_account_key == created_resource_azure_account_key:
            raise CloudBoltException('Sync failed: Discovered resource\'s azure_account_key not the same as created resource, {} =/= {}'.format(discovered_resource.azure_account_key, created_resource_azure_account_key))

        if not discovered_resource.azure_account_key_fallback == created_resource_azure_account_key_fallback:
            raise CloudBoltException('Sync failed: Discovered resource\'s azure_account_key_fallback not the same as created resource, {} =/= {}'.format(discovered_resource.azure_account_key_fallback, created_resource_azure_account_key_fallback))
    
    except Exception as e:
        set_progress("### FAILED TO SYNC RESOURCE ###")
        set_progress(e)
        sync_failed = True

    
    try:
        set_progress("### DELETING DISCOVERED RESOURCE FOR BLUEPRINT ###", tasks_done=2)
        test_delete_resource(client, discovered_resource)
    except Exception as e:
        set_progress("Delete failed: deletion of the discovered bp threw an exception: {}".format(e))


    ending_resource_set = bp.resource_set.all()
    if not len(starting_resource_set) == len(ending_resource_set):
        intersection = starting_resource_set & ending_resource_set
        set_progress("Delete failed: resource set ending bigger than it started even after deleting added, here are the extra values: {}".format(intersection))

    set_progress("ALL Tests completed!", tasks_done=3)

    if sync_failed:
        raise CloudBoltException("Failed to Sync Resource")