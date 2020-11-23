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
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

BLUEPRINT = 78

BP_PAYLOAD = """
    {
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/78/",
                "blueprint-items-arguments": {
                    "build-item-Create Predictive DNS Zone": {
                        "parameters": {
                            "dnsTypeConfig-a358": "Primary",
                            "domainName-a358": "testchat1.com",
                            "isPrimary-a358": "True",
                            "zoneTransferEnabled-a358": "True"
                        }
                    }
                },
                "resource-name": "Citrix ITM Zone",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "testchat1.com"


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 600, 10)
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress("Blueprint deployment order {} completed successfully.".format(order_id))
    return order_id


def test_delete_resource(client, resource):
    body = "{}"
    delete = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))


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
    order_id = test_order_blueprint(client)

    order = Order.objects.get(id=order_id)
    resource = order.orderitem_set.first().cast().get_resource()

    redis_cache_name = resource.azure_redis_cache_name

    # Delete the resource from the database only

    # Delete the sub resources first
    resource.sub_components.all().delete()
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE', blueprint=bp)

    test_delete_resource(client, resource)

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)

    set_progress("ALL Tests completed!", tasks_done=3)
