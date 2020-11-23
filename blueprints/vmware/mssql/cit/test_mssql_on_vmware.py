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

BLUEPRINT = 99

BP_PAYLOAD = """
    {
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/103/",
                "blueprint-items-arguments": {
                    "build-item-Install SQL Server": {
                        "parameters": {
                            "install-sql-server-agent-a460": "Y",
                            "mssql-product-id-a460": "express",
                            "sa-password-a460": "CloudBolt!"
                        }
                    },
                    "build-item-MSSQL on VMware": {
                        "attributes": {
                            "hostname": "sqlforcit",
                            "quantity": 1
                        },
                        "environment": "/api/v2/environments/108/",
                        "os-build": "/api/v2/os-builds/24",
                        "parameters": {
                            "cpu-cnt": "2",
                            "mem-size": "20 GB",
                            "tech-specific-script-execution": "False",
                            "vm-customization-timeout": "1900",
                            "vmware-datastore": "VS60_STOR",
                            "vmware-disk-type": "Thin Provision"
                        }
                    }
                },
                "resource-name": "SQLServer On VMware",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""


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

    test_delete_resource(client, resource)

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)

    set_progress("ALL Tests completed!", tasks_done=3)
