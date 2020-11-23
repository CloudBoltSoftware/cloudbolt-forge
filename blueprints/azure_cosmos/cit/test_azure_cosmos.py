import json
import logging
import re
import uuid

import requests

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion

from common.methods import set_progress
from accounts.models import Group
from infrastructure.models import Environment
from servicecatalog.models import ServiceBlueprint, ServiceItem
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo


# suppress logging from requests module
logger = logging.getLogger("requests")
logger.setLevel(40)
logger = logging.getLogger("py.warnings")
logger.setLevel(40)

# Order Specific Variables

## Azure Spefic Variables
NEW_RESOURCE_NAME = "clcitazurecomos" + str(uuid.uuid4())[:8]
# All Azure Web Apps must be deployed to an Azure Resource Group. A change to the PAYLOAD
# may also require that the Resource Group is manually created in the Azure Portal.
_AZURE_RESOURCE_GROUP = "content_library_cosmos_db_test"

## CloudBolt Environment Variables
API_CLIENT_CI = "CIT API Client"
GROUP = Group.objects.get(name="Temp Group", id=2)
BLUEPRINT = ServiceBlueprint.objects.get(
    name__startswith="Azure Cosmos Database Account", id=35
)
ENVIRONMENT = Environment.objects.get(id=8, name="eastus2")
_BUILD_ITEM = BLUEPRINT.serviceitem_set.filter(name__contains="Create").first()

## CloudBolt API v2 required Payload
_PAYLOAD = {
    "group": f"/api/v2/groups/{GROUP.global_id}/",
    "items": {
        "deploy-items": [
            {
                "blueprint": f"/api/v2/blueprints/{BLUEPRINT.global_id}/",
                "blueprint-items-arguments": {
                    f"build-item-{_BUILD_ITEM.name}": {
                        "parameters": {
                            "account-name-a119": NEW_RESOURCE_NAME,
                            "env-id-a119": str(ENVIRONMENT.id),
                            "resource-group-a119": _AZURE_RESOURCE_GROUP,
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
# Convert the Payload to a JSON object to sumbmit to the CloudBolt API.
BP_PAYLOAD = json.dumps(_PAYLOAD)
# END of Order specific variables


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    try:
        # In the case that an order fails, the test writer should be able to run the output
        # of the BP_PAYLOAD in Admin > API Browser > Orders.
        set_progress("Ordering for the API using the following BP_PAYLOAD:")
        set_progress(BP_PAYLOAD)
        order = json.loads(client.post("/api/v2/orders/", body=BP_PAYLOAD))
    except requests.HTTPError as err:
        raise CloudBoltException(
            "The order failed. Please review that the Resource Group is available in the Azure lab to deploy this test."
        ) from err
    order_href = order["_links"]["self"]["href"]
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 600, 10)
    if result != 0:
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id)
        )
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id)
    )


def test_delete_resource(client, resource):
    body = "{}"
    delete = json.loads(  # noqa: F841
        client.post(
            "/api/v2/resources/{}/{}/actions/1/".format(
                resource.resource_type.name, resource.id
            ),
            body=body,
        )
    )


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

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = BLUEPRINT.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    set_progress(f"RESOURCE {resource}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    BLUEPRINT.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = BLUEPRINT.resource_set.get(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    )

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
