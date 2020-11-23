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
from orders.models import Order
from jobs.models import Job

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 66

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-3nu92jkk/",
                "blueprint-items-arguments": {
                    "build-item-Create an Azure Redis Cache": {
                        "parameters": {
                            "capacity-a284": "1",
                            "env-id-a284": "18",
                            "redis-cache-name-a284": "mycittest",
                            "resource-group-a284": "test-webhook-delete",
                            "sku-a284": "Basic"
                        }
                    }
                },
                "resource-name": "Azure Cache for Redis",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "Azure redis cache - mycittest"


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])

def test_order_blueprint(client):

    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 600, 10)
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress("Blueprint deployment order {} completed successfully.".format(order_id))
    return order_id

def test_delete_resource(client, resource):
    body = "{}"
    test_response = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))

    job_id = test_response.get('run-action-job').get('self').get('href').split('/')[-2]
    # Wait for job to complete
    while Job.objects.get(id=job_id).is_active():
        time.sleep(2)

    return Job.objects.get(id=job_id).status


def get_api_client():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return CloudBoltAPIClient(
        ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol)

def run(job, *args, **kwargs):
    bp = ServiceBlueprint.objects.get(id=BLUEPRINT)
    set_progress(
        "Running Continuous Infrastructure Test for blueprint {}".format(bp)
    )
    client = get_api_client()
    # Delete resource if it already exists locally
    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).delete()
    # Run blueprint synchronization in case a Azure cache for redis has been created online
    bp.sync_resources()
    
    resource_exists = bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE').exists()
    if resource_exists:
        # Delete the resource
        resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
        test_result = test_delete_resource(client, resource)
        if test_result != "SUCCESS":
            # The resource might only be available locally
            resource.delete()
        else:
            # Deleting the Redis online takes time so we can sleep for a few minutes
            time.sleep(600)
        
    # At this point we are sure the resources doesn't exist

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    order_id = test_order_blueprint(client)

    order = Order.objects.get(id=order_id)
    resource = order.orderitem_set.first().cast().get_resource()

    # Delete the resource from the database only
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    # Sleep for 20 minutes since you can't delete the resource until it is fully available.
    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    time.sleep(1800)
    test_result = test_delete_resource(client, resource)
    
    if test_result != "SUCCESS":
        return "FAILURE", "Unable to delete the Azure Cache for redis", ""

    set_progress("ALL Tests completed!", tasks_done=3)
    return "SUCCESS", "", ""
    