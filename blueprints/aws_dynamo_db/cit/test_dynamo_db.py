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

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

BLUEPRINT = 59

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-cmo0jhxq/",
                "blueprint-items-arguments": {
                    "build-item-Create AWS Dynamo DB": {
                        "parameters": {
                            "env-id-a267": "184",
                            "primary-key-a267": "test",
                            "table-name-a267": "tabletest"
                        }
                    }
                },
                "resource-name": "Dynamo DB",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "tabletest"


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 180, 10)
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress("Blueprint deployment order {} completed successfully.".format(order_id))


def test_delete_resource(client, resource):
    body = "{}"
    delete_response = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))
    job_id = delete_response.get('run-action-job').get('self').get('href').split('/')[-2]
    # Wait for job to complete

    while Job.objects.get(id=job_id).is_active():
        time.sleep(2)

    return Job.objects.get(id=job_id).status


def get_api_client():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return CloudBoltAPIClient(
        ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol)


def run(**kwargs):
    bp = ServiceBlueprint.objects.get(id=BLUEPRINT)
    set_progress(f"Running Continuous Infrastructure Test for blueprint {bp}")

    client = get_api_client()

    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).delete()
    # Run blueprint synchronization in case a dynamo db has been created manually on AWS
    bp.sync_resources()
    resource_exists = bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE').exists()

    if resource_exists:
        # Delete the resource
        resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
        test_result = test_delete_resource(client, resource)
        if test_result != "SUCCESS":
            # The resource might only be available locally
            resource.delete()

    # At this point we are sure the resource doesn't exist
    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
    # Delete the resource from the database only
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_result = test_delete_resource(client, resource)

    if test_result != "SUCCESS":
        return "FAILURE", "Unable to delete the dynamo db", ""

    set_progress("ALL Tests completed!", tasks_done=3)
    return "SUCCESS", "ALL Tests completed!", ""
