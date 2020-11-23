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

# BP specific variables - You should change these
BLUEPRINT = 48

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-m8i79e9w/",
                "blueprint-items-arguments": {
                    "build-item-Create AWS Route 53": {
                        "parameters": {
                            "a-value-a198": "192.168.0.1",
                            "aws-id-a198": "2",
                            "r53-recordset-name-a198": "cit01.content-development.cloudbolt.io",
                            "record-type-a198": "A",
                            "ttl-a198": "300",
                            "zone-id-a198": "ZALG1SAOIS4EJ"
                        }
                    }
                },
                "resource-name": "AWS Route 53 DNS Record",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "cit01.content-development.cloudbolt.io."


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
    set_progress("Running Continuous Infrastructure Test for blueprint {}".format(bp))

    client = get_api_client()
    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME[:1]).delete()

    # Run blueprint synchronization in case a route53 record has been created online
    bp.sync_resources()

    resource_exists = bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE').exists()
    if resource_exists:
        # Delete the resource
        resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
        test_result = test_delete_resource(client, resource)
        if test_result != "SUCCESS":
            # The resource might only be available locally
            resource.delete()

    # At this point we are sure the resources doesn't exist
    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME[:-1], lifecycle='ACTIVE')
    # Delete the resource from the database only
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_result = test_delete_resource(client, resource)
    if test_result != "SUCCESS":
        return "FAILURE", "Unable to delete the route53 record set", f"{test_result}"

    set_progress("ALL Tests completed!", tasks_done=3)
    return "SUCCESS", "", ""
