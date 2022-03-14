import json
import logging
import re
import time

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from jobs.models import Job
from resources.models import Resource

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

BLUEPRINT = 4

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-6ycnxt5w/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-psqzji1k/",
                "blueprint-items-arguments": {
                    "build-item-Create Data Factory Workspace": {
                        "parameters": {
                            "azure-region-a157": "27",
                            "data-factory-name-a157": "mock0001",
                            "resource-group-a157": "cb-rg-ym"
                        }
                    }
                },
                "resource-name": "Azure DataFactory",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "mock0001"

def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    
    result = wait_for_order_completion(client, order_id, 720, 10)
    
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {0} did not succeed.".format(order_id))
    
    set_progress("Blueprint deployment order {0} completed successfully.".format(order_id))


def test_delete_resource(client, resource):
    body = "{}"
    
    test_response = json.loads(client.post('/api/v2/resources/{0}/{1}/actions/1/'.format(resource.resource_type.name, 
                        resource.id), body=body))

    job_id = test_response.get('run-action-job').get('self').get('href').split('/')[-2]
    
    # Wait for job to complete
    while Job.objects.get(id=job_id).is_active():
        time.sleep(2)

    return Job.objects.get(id=job_id).status

def get_api_client():

    # fetch connection info object
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)

    client = CloudBoltAPIClient(ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol)
    
    return client


def run(job, *args, **kwargs):
    # fetch blueprint model object
    bp = ServiceBlueprint.objects.get(id=BLUEPRINT)
    
    set_progress(f"Running Continuous Infrastructure Test for blueprint {bp}")
    logger.info(f"Running Continuous Infrastructure Test for blueprint {bp}")
    
    # get localhost client object
    client = get_api_client()
    
    # Run blueprint synchronization in database has been created online
    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).delete()
    
    # sync blueprint resources
    bp.sync_resources()
    
    # search resource on cmp server
    resource_exist =  Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp,lifecycle='ACTIVE').first()

    if resource_exist is not None:
        set_progress("Resource already exists. Attempting to delete...")
        
        # delete resource from Azure Datafactory 
        test_result = test_delete_resource(client, resource_exist)
       
        # delete resource from cmp server
        resource_exist.delete()

    # At this point we are sure the resource doesn't exist
    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=1, total_tasks=3)
    
    # place a Azure Datafactory resource order
    test_order_blueprint(client)
    
    # get Azure Datafactory resource object
    resource = Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp, lifecycle='ACTIVE').first()
    
    logger.info(f"Azure Datafactory '{resource}' order successfully")
    
    if resource is not None:
        set_progress(f"Azure Datafactory '{resource}' order successfully")
        
        time.sleep(240)
         
        set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
        
        # delete resource from Azure Datafactory
        test_result = test_delete_resource(client, resource)

        if test_result != "SUCCESS":
            return "FAILURE", "Unable to delete the data factory resource", ""
        
        set_progress(f"Azure Datafactory '{resource}' deleted successfully")
        
        # delete resource from cmp server
        resource.delete()

    set_progress("ALL Tests completed successfully", tasks_done=3)
    
    return "SUCCESS", "ALL Tests completed successfully", ""