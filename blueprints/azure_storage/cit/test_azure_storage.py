import json
import logging
import re
import uuid

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo


# suppress logging from requests module
logger = logging.getLogger("requests")
logger.setLevel(40)
logger = logging.getLogger("py.warnings")
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = ServiceBlueprint.objects.get(name__startswith="Azure Storage", id=249)

# Storage Accounts must be less than 24 characters long and only contain numbers and
# upper and lower case letters.
NEW_RESOURCE_NAME = "clcitstorage" + str(uuid.uuid4())[:8].lower()
assert len(NEW_RESOURCE_NAME) < 24

PAYLOAD = {
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-xxqfc7ck/",
                "blueprint-items-arguments": {
                    "build-item-Create Azure Storage Account": {
                        "parameters": {
                            "access-tier-a958": "Hot",
                            "account-name-a958": NEW_RESOURCE_NAME,
                            "env-id-a958": "8",
                            "kind-a958": "StorageV2",
                            "resource-group-a958": "cit_content_library_azure_storage",
                            "sku-name-a958": "Standard_LRS",
                        }
                    }
                },
                "resource-name": "Azure Storage - CIT Test",
                "resource-parameters": {},
            }
        ]
    },
    "submit-now": "true",
}

BP_PAYLOAD = json.dumps(PAYLOAD)

# END of BP specific variables


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post("/api/v2/orders/", body=BP_PAYLOAD))
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
    bp = BLUEPRINT
    set_progress("Running Continuous Infrastructure Test for blueprint {}".format(bp))

    client = get_api_client()

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = bp.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    set_progress(f"RESOURCE {resource}")
    rce = bp.resource_set.last()
    set_progress(f"LAST RESOURCE {rce}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.filter(
        name__icontains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
