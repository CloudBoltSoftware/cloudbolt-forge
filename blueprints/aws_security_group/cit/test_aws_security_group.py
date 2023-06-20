import json
import logging
import re
import time

from botocore.exceptions import ClientError
from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from jobs.models import Job
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo


# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 94

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/94/",
                "blueprint-items-arguments": {
                    "build-item-AWS Security Group Build": {
                        "parameters": {
                            "cidr-ip-a427": "0.0.0.0/0",
                            "direction-a427": "Ingress",
                            "from-port-a427": "80",
                            "ip-protocol-a427": "tcp",
                            "region-a427": "eu-west-1",
                            "security-group-description-a427": "awssecgroupcit001",
                            "security-group-name-a427": "awssecgroupcit001",
                            "to-port-a427": "80",
                            "vpc-id-a427": "vpc-8b3e19ed"
                        }
                    }
                },
                "resource-name": "AWS Security Groups",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "awssecgroupcit001"
# END of BP specific variables


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 600, 10)
    if result != 0:
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id))


def test_delete_resource(client, resource):
    body = "{}"
    delete_response = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))

    job_id = delete_response.get(
        'run-action-job').get('self').get('href').split('/')[-2]
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

    # if a resource exists with the same name, delete it before you try to create it. otherwise the test will fail with a duplicate exception.
    bp.sync_resources()
    resource_exists = bp.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE').exists()

    if resource_exists:
        delete_response = test_delete_resource(client, bp.resource_set.get(
            name__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE'))

        if delete_response != "SUCCESS":
            resource.delete()

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)

    test_order_blueprint(client)

    resource = bp.resource_set.get(
        name__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress(f"RESOURCE {resource}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(
        name__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    delete_result = test_delete_resource(client, resource)

    if delete_result != "SUCCESS":
        return "FAILURE", "Unable to delete the security group", ""

    set_progress("ALL Tests completed!", tasks_done=3)
