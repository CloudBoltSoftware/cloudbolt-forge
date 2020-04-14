import json
import logging
import re
import uuid

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion, wait_for_job_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from orders.models import Order

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 238

name = uuid.uuid4().hex.upper()[0:12]

NEW_RESOURCE_NAME = f"cit{name}".lower()

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-27naps5c/",
                "blueprint-items-arguments": {
                    "build-item-Create Google SQL Database": {
                        "parameters": {
                            "db-identifier-a683": "%s",
                            "db-version-a683": "MYSQL_5_7",
                            "env-id-a683": "131",
                            "gcp-region-a683": "northamerica-northeast1"
                        }
                    }
                },
                "resource-name": "Google MySQL Database",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
""" % NEW_RESOURCE_NAME


# END of BP specific variables

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
    set_progress(
        "Running Continuous Infrastructure Test for blueprint {}".format(bp)
    )

    client = get_api_client()

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    resource = test_order_blueprint(client)

    set_progress(f"RESOURCE {resource}")
    rce = bp.resource_set.last()
    set_progress(f"LAST RESOURCE {rce}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
