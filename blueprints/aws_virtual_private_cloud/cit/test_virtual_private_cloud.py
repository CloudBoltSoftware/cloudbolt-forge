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

BLUEPRINT = 37

BP_PAYLOADS = ["""
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-pb2egoyj/",
                "blueprint-items-arguments": {
                    "build-item-Create AWS Virtual Private Cloud": {
                        "parameters": {
                            "aws-region-a157": "ap-southeast-1",
                            "cidr-block-a157": "10.0.0.1/28",
                            "provide-ipv6-a157": "True",
                            "rh-id-a157": "29",
                            "tenancy-a157": "dedicated"
                        }
                    }
                },
                "resource-name": "AWS Virtual Private Cloud (VPC)",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
""",
"""
{
    "group": "/api/v2/groups/GRP-w0qe6tkf/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/BP-pb2egoyj/",
                "blueprint-items-arguments": {
                    "build-item-Create AWS Virtual Private Cloud": {
                        "parameters": {
                            "aws-region-a157": "ap-southeast-1",
                            "cidr-block-a157": "10.0.0.10/28",
                            "provide-ipv6-a157": "True",
                            "rh-id-a157": "29",
                            "tenancy-a157": "default"
                        }
                    }
                },
                "resource-name": "AWS Virtual Private Cloud (VPC)",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""
]


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    orders_ids = []
    for BP_PAYLOAD in BP_PAYLOADS:
        order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
        order_href = order['_links']['self']['href']
        order_id = get_order_id_from_href(order_href)
        result = wait_for_order_completion(client, order_id, 180, 10)
        if result != 0:
            raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
        set_progress("Blueprint deployment order {} completed successfully.".format(order_id))
        orders_ids.append(order_id)
    return orders_ids


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

    orders_ids = test_order_blueprint(client)
    for order_id in orders_ids:
        order = Order.objects.get(id=order_id)
        resource = order.orderitem_set.first().cast().get_resource()

        vpc_id = resource.vpc_id

        # Delete the resource from the database only
        resource.delete()
        set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
        bp.sync_resources()

        # should be able to get the resource since the sync should have created it
        resources = bp.resource_set.filter(lifecycle='ACTIVE', blueprint=bp)

        set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)

        [test_delete_resource(client, resource) for resource in resources if resource.vpc_id == vpc_id]

    set_progress("ALL Tests completed!", tasks_done=3)
