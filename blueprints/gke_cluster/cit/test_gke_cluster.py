import json
import logging
import re

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
BLUEPRINT = ServiceBlueprint.objects.get(name__startswith="Google Kubernetes Engine Cluster", id=294)

# Create a unique resource name in case of overlap between prior failures.
NEW_RESOURCE_NAME = "cl-cit-gke-test"

PAYLOAD = {
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-51szt49j/",
                "blueprint-items-arguments": {
                    "build-item-Create GKE Cluster": {
                        "parameters": {
                            "gcp-project-a2161": "131",
                            "gcp-zone-a2161": "68316",
                            "name-a2161": NEW_RESOURCE_NAME,
                            "node-count-a2161": "2"
                        }
                    }
                },
                "resource-name": "Google Kubernetes Engine Cluster",
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

    # Run blueprint synchronization in case a GKE container has been created online
    bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).delete()

    # Order the BP
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=3)
    test_order_blueprint(client)

    resource = bp.resource_set.filter(
        name__contains=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    set_progress(f"RESOURCE {resource}")
    rce = bp.resource_set.last()
    set_progress(f"LAST RESOURCE {rce}")
    # Delete the resource from the database only
    # resource.delete()

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
