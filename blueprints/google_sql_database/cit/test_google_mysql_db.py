import json
import logging
import uuid

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import (
    wait_for_order_completion,
    wait_for_job_completion,
)
from common.methods import set_progress

from accounts.models import Group
from infrastructure.models import Environment
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from orders.models import Order

# suppress logging from requests module
logger = logging.getLogger("requests")
logger.setLevel(40)
logger = logging.getLogger("py.warnings")
logger.setLevel(40)

# Order specific variables
## GCP specific variables
NEW_RESOURCE_NAME = f"clcitgooglesqltest" + str(uuid.uuid4())[:8]
GCP_REGION = "northamerica-northeast1"
DB_VERSION = "MYSQL_5_7"

## CloudBolt environment variables
API_CLIENT_CI = "CIT API Client"
GROUP = Group.objects.get(name="Temp Group", id=2)
BLUEPRINT = ServiceBlueprint.objects.get(
    name__startswith="Google MySQL Database", id=238
)
_BUILD_ITEM = BLUEPRINT.serviceitem_set.filter(name__contains="Create").first()
ENVIRONMENT = Environment.objects.get(
    id=131, name="(GCP) cloudbolt-content-development"
)

## CloudBolt API v2 required payload
PAYLOAD = {
    "group": f"/api/v2/groups/{GROUP.global_id}/",
    "items": {
        "deploy-items": [
            {
                "blueprint": f"/api/v2/blueprints/{BLUEPRINT.global_id}/",
                "blueprint-items-arguments": {
                    f"build-item-{_BUILD_ITEM.name}": {
                        "parameters": {
                            "db-identifier-a683": NEW_RESOURCE_NAME,
                            "db-version-a683": DB_VERSION,
                            "env-id-a683": str(ENVIRONMENT.id),
                            "gcp-region-a683": GCP_REGION,
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
# END of Order specific variables


def get_id_from_href(order_href):
    split = order_href.split("/")
    return int(split[-2])


def test_delete_resource(client, resource):
    body = "{}"
    response = json.loads(
        client.post(
            "/api/v2/resources/{}/{}/actions/1/".format(
                resource.resource_type.name, resource.id
            ),
            body=body,
        )
    )
    job_href = response["run-action-job"]["self"]["href"]
    job_id = get_id_from_href(job_href)
    result = wait_for_job_completion(client, job_id, 180, 10)
    if not result == 0:
        raise CloudBoltException(
            "Resource deletion job {} did not succeed.".format(job_id)
        )
    set_progress("Resource deletion job {} completed successfully.".format(job_id))


def test_order_blueprint(client):
    # In the case that an order fails, the test writer should be able to run the output
    # of the BP_PAYLOAD in Admin > API Browser > Orders.
    set_progress("Ordering for the API using the following BP_PAYLOAD:")
    set_progress(BP_PAYLOAD)
    order = json.loads(client.post("/api/v2/orders/", body=BP_PAYLOAD))
    order_href = order["_links"]["self"]["href"]
    order_id = get_id_from_href(order_href)
    set_progress("Current Running order: {}".format(order_id))
    result = wait_for_order_completion(client, order_id, 180, 10)
    order_object = Order.objects.filter(id=order_id).first()
    job_list = order_object.list_of_jobs()
    job_object = job_list[0]
    resource = job_object.get_resource()

    if not result == 0 and (not resource or resource.lifecycle == "PROVFAILED"):
        test_delete_resource(client, resource)
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id)
        )

    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id)
    )

    return resource


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
    resource = test_order_blueprint(client)

    set_progress(f"RESOURCE {resource}")
    rce = BLUEPRINT.resource_set.last()
    set_progress(f"LAST RESOURCE {rce}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    BLUEPRINT.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = BLUEPRINT.resource_set.get(name=NEW_RESOURCE_NAME, lifecycle="ACTIVE")

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)
    set_progress("ALL Tests completed!", tasks_done=3)
