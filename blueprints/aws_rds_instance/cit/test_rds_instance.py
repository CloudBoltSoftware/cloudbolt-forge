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
from resources.models import Resource

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

BLUEPRINT = 228

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-9ktj0axm/",
                "blueprint-items-arguments": {
                    "build-item-Create RDS instance": {
                        "parameters": {
                            "allocated-storage-a657": "20",
                            "aws-environment-a657": "238",
                            "aws-rds-engine-a657": "MySQL",
                            "db-identifier-a657": "cittest",
                            "db-name-a657": "citdatabase",
                            "db-password-a657": "************",
                            "db-username-a657": "robert",
                            "instance-class-a657": "db.t2.micro",
                            "license-model-a657": "general-public-license"
                        }
                    }
                },
                "resource-name": "cittest",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "cittest"

def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 720, 10)
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
    set_progress(
        "Running Continuous Infrastructure Test for blueprint {}".format(bp)
    )

    client = get_api_client()

    # Run blueprint synchronization in database has been created online
    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).delete()

    bp.sync_resources()
    resource_exists = Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp,lifecycle='ACTIVE').exists()

    if resource_exists:
        # Delete the resource
        resource = Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp,lifecycle='ACTIVE').first()
        set_progress("Resource already exists. Attempting to delete...")
        test_result = test_delete_resource(client, resource)
        if test_result != "SUCCESS":
            # The resource might only be available locally
            resource.delete()

    # At this point we are sure the resource doesn't exist
    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=1, total_tasks=4)
    test_order_blueprint(client)

    resource = Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp,lifecycle='ACTIVE').first()
    # Delete the resource from the database only
    if resource:
        resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=2)
    bp.sync_resources()
    # should be able to get the resource since the sync should have created it
    resource = Resource.objects.filter(name__iexact=NEW_RESOURCE_NAME, blueprint=bp,lifecycle='ACTIVE').first()
    set_progress(f"Found the resource: {resource}")
    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=3)
    test_result = test_delete_resource(client, resource)

    if test_result != "SUCCESS":
        return "FAILURE", "Unable to delete the database", ""

    set_progress("ALL Tests completed!", tasks_done=4)
    return "SUCCESS", "ALL Tests completed!", ""
