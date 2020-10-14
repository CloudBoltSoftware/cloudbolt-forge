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

BLUEPRINT = 52

BP_PAYLOADS = ["""
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/52/",
                "blueprint-items-arguments": {
                    "build-item-AWS RDS DB Cluster Build": {
                        "parameters": {
                            "db-cluster-identifier-a245": "AuroraMysqlCluster",
                            "engine-a245": "aurora-mysql",
                            "env-id-a245": "23",
                            "master-password-a245": "Ee199407#",
                            "master-username-a245": "esir"
                        }
                    }
                },
                "resource-name": "AWS DB Cluster",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
""",
"""
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/52/",
                "blueprint-items-arguments": {
                    "build-item-AWS RDS DB Cluster Build": {
                        "parameters": {
                            "db-cluster-identifier-a245": "AuroraDbCluster",
                            "engine-a245": "aurora",
                            "env-id-a245": "23",
                            "master-password-a245": "Ee199407#",
                            "master-username-a245": "esir"
                        }
                    }
                },
                "resource-name": "AWS DB Cluster",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
""",
"""
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/52/",
                "blueprint-items-arguments": {
                    "build-item-AWS RDS DB Cluster Build": {
                        "parameters": {
                            "db-cluster-identifier-a245": "AuroraPsqlCluster",
                            "engine-a245": "aurora-postgresql",
                            "env-id-a245": "23",
                            "master-password-a245": "Ee199407#",
                            "master-username-a245": "esir"
                        }
                    }
                },
                "resource-name": "AWS DB Cluster",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
""",
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
        result = wait_for_order_completion(client, order_id, 6000, 10)
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
    
        db_cluster_identifier = resource.db_cluster_identifier
        id = resource.id
        
        # Delete the resource from the database only
        set_progress(f"### DELETING RESOURCE {resource}")
        resource.delete()
        set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
        bp.sync_resources()
        
        # should be able to get the resource since the sync should have created it
        resources = bp.resource_set.filter(lifecycle='ACTIVE', blueprint=bp)
        
        set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    
        [test_delete_resource(client, resource) for resource in resources if resource.db_cluster_identifier.lower() == db_cluster_identifier.lower()]
        
    set_progress("ALL Tests completed!", tasks_done=3)
