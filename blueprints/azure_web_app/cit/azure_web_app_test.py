import json
import logging
import re
import uuid

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from accounts.models import Group
from infrastructure.models import Environment
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
GROUP = Group.objects.get(name="Temp Group", id=2)
BLUEPRINT = ServiceBlueprint.objects.get(
    name__startswith="Azure Web Application", id=253
)
ENVIRONMENT = Environment.objects.get(id=8, name="eastus2")

# Create a unique resource name and service plan. Please note that the service plan
# will automatically generate a unique uuid at the end of the name provided.
NEW_RESOURCE_NAME = "clcitazurewebapp" + str(uuid.uuid4())[:8]
# All Azure Web Apps must be deployed to an Azure Resource Group. A change to the PAYLOAD
# may also require that the Resource Group is manually created in the Azure Portal.
AZURE_RESOURCE_GROUP = "content_library_web_app_test"

# We create the PAYLOAD as a python object and then convert it to json using json.dumps,
# so that we can post the json to the API.
PAYLOAD = {
    "group": f"/api/v2/groups/{GROUP.global_id}/",
    "items": {
        "deploy-items": [
            {
                "blueprint": f"/api/v2/blueprints/{BLUEPRINT.global_id}/",
                "blueprint-items-arguments": {
                    "build-item-Create Azure Web App": {
                        "parameters": {
                            "azure-env-a989": str(ENVIRONMENT.id),
                            "resource-group-a989": AZURE_RESOURCE_GROUP,
                            "web-app-name-a989": NEW_RESOURCE_NAME,
                        }
                    }
                },
                "resource-name": "Azure-Web-App-00X",
                "resource-parameters": {},
            }
        ]
    },
    "submit-now": "true",
}

# The BP_PAYLOAD can be verified manually by navigating to the Api Browser (Admin > API Browser),
# selecting the /orders and posting the BP_PAYLOD in the web form.
BP_PAYLOAD = json.dumps(PAYLOAD)

# END of BP specific variables


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
            "Blueprint Deployment order {} did not succeed. Please verify that the Azure Lab has not met it's limit for Web Applications".format(
                order_id
            )
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
        name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE"
    ).first()

    set_progress(f"RESOURCE {resource}")
    # Delete the resource from the database only
    resource.delete()

    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle="ACTIVE")

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
