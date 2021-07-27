import json
import logging
import re

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from orders.models import Order

# suppress logging from requests module
logger = logging.getLogger("requests")
logger.setLevel(40)
logger = logging.getLogger("py.warnings")
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

BP_NAME = "GCP Storage"

# NOTE: This Payload should be a copy of the API call for a successful blueprint order
# on the system running this test. Source the API call from the "API ..." button at the
# top of the successful Order detail page (like at "https://10.30.74.20/orders/2/"").
BP_PAYLOAD = """
{
    "group": "/api/v2/groups/GRP-u2trrfjy/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-rxbot99x/",
                "blueprint-items-arguments": {
                    "build-item-GCP Storage Create": {
                        "parameters": {
                            "bucket-name-a142": "cit-test-bucket-109238",
                            "env-id-a142": "2",
                            "storage-type-a142": "STANDARD"
                        }
                    }
                },
                "resource-name": "GCP Bucket",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "cit-test-bucket-109238"


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post("/api/v2/orders/", body=BP_PAYLOAD))
    order_href = order["_links"]["self"]["href"]
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 800, 10)
    if result != 0:
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id)
        )
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id)
    )


def test_delete_resource(client, resource):
    body = "{}"
    delete = json.loads(
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

def remove_test_resource_if_exists(client, bp):
    # Run blueprint synchronization in case the storage has been created online
    set_progress(f"-->Deleting {NEW_RESOURCE_NAME} in CloudBolt if it exists")
    bp.resource_set.filter(name=NEW_RESOURCE_NAME).delete()

    set_progress(f"-->Syncinc resources by running Discovery Plugin.")
    bp.sync_resources()
    resource_exists = bp.resource_set.filter(
        name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).exists()

    if resource_exists:
        set_progress(f"-->Runing Teardown Plugin on discovered {NEW_RESOURCE_NAME}")
        # Delete the resource
        resource = bp.resource_set.get(
            name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
        )
        test_delete_resource(client, resource)


def run(job, *args, **kwargs):
    set_progress(f"Looking for a blueprint called '{BP_NAME}'")
    bp = ServiceBlueprint.objects.get(name=BP_NAME)
    if bp:
        set_progress("Found Blueprint {bp}. Running Continuous Infrastructure Test")
    else:
        return "FAILURE", f"Could not find a blueprint named '{BP_NAME}'", ""

    set_progress(
        "Getting api client for Cloudbolt to run the CIT Test (defined in "
        f"Admin / ConnectionInfo / {API_CLIENT_CI})"
    )
    try:
        client = get_api_client()
    except Exception as ex:
        return "FAILURE", f"Could not connect to {API_CLIENT_CI}", ex

    # Make sure the resource doesn't currently exist anywhere
    set_progress(f"Making sure the resource isn't in CloudBolt or the Resource Handler")
    remove_test_resource_if_exists(client, bp)

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE")
    # Delete the resource from the database only
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE")

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
    return "SUCCESS", "ALL Tests completed!", ""
