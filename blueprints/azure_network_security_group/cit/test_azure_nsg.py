import json
import logging
import re
import time
import uuid

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress

from accounts.models import Group
from infrastructure.models import Environment
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from jobs.models import Job


# suppress logging from requests module
logger = logging.getLogger("requests")
logger.setLevel(40)
logger = logging.getLogger("py.warnings")
logger.setLevel(40)

# Order specific variables

## Azure Specific variables
NEW_RESOURCE_NAME = "clcitnetworksecuritygroup" + str(uuid.uuid4())[:8]
# All Azure Network Security Groups are deployed into an Azure Resource Group. A change to
# the PAYLOAD may also require that the Resource Group is manually created in the Azure Portal.
AZURE_RESOURCE_GROUP = "content_library_network_security_group_test"

## CloudBolt environment variables
API_CLIENT_CI = "CIT API Client"
GROUP = Group.objects.get(name="Temp Group", id=2)
BLUEPRINT = ServiceBlueprint.objects.get(
    name__startswith="Azure Network Security Group", id=271
)
BUILD_ITEM = BLUEPRINT.serviceitem_set.filter(name__contains="Create").first()
ENVIRONMENT = Environment.objects.get(id=8, name="eastus2")

## CloudBolt API v2 required Payload
PAYLOAD = {
    "group": f"/api/v2/groups/{GROUP.global_id}/",
    "items": {
        "deploy-items": [
            {
                "blueprint": f"/api/v2/blueprints/{BLUEPRINT.global_id}/",
                "blueprint-items-arguments": {
                    f"build-item-{BUILD_ITEM.name}": {
                        "parameters": {
                            "env-id-a1235": str(ENVIRONMENT.id),
                            "network-security-group-name-a1235": NEW_RESOURCE_NAME,
                            "resource-group-a1235": AZURE_RESOURCE_GROUP,
                        }
                    }
                },
                "resource-name": BLUEPRINT.name,
                "resource-parameters": {},
            }
        ]
    },
    "submit-now": "true",
}

BP_PAYLOAD = json.dumps(PAYLOAD)
# END of Order Specific Variables


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post("/api/v2/orders/", body=BP_PAYLOAD))
    order_href = order["_links"]["self"]["href"]
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 180, 10)
    if result != 0:
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id)
        )
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id)
    )


def test_delete_resource(client, resource):
    body = "{}"
    test_response = json.loads(
        client.post(
            "/api/v2/resources/{}/{}/actions/1/".format(
                resource.resource_type.name, resource.id
            ),
            body=body,
        )
    )

    job_id = test_response.get("run-action-job").get("self").get("href").split("/")[-2]
    # Wait for job to complete
    while Job.objects.get(id=job_id).is_active():
        time.sleep(2)

    return Job.objects.get(id=job_id).status


def get_api_client():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return CloudBoltAPIClient(
        ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol
    )


def run(job, *args, **kwargs):
    set_progress(
        "Running Continuous Infrastructure Test for blueprint {}".format(BLUEPRINT)
    )

    client = get_api_client()

    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = BLUEPRINT.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    BLUEPRINT.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = BLUEPRINT.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()
    if not resource:
        return "FAILURE", "The Network Security Group doesn't exist", ""

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_result = test_delete_resource(client, resource)
    if test_result != "SUCCESS":
        return "FAILURE", "Unable to delxete Azure Network Security Group", ""

    set_progress("ALL Tests completed!", tasks_done=3)
