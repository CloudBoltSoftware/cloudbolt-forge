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
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 73

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/85/",
                "blueprint-items-arguments": {
                    "build-item-create EKS stack": {
                        "parameters": {
                            "cluster-name-a391": "test_alpha1",
                            "cluster-security-group-a391": "sg-0092921b8fa25afdd",
                            "env-id-a391": "4",
                            "key-name-a391": "a",
                            "node-group-name-a391": "cit-test-stack",
                            "node-image-id-a391": "ami-08c4955bcc43b124e",
                            "node-instance-type-a391": "t2.small",
                            "node-volume-size-a391": "5",
                            "scaling-desired-capacity-a391": "2",
                            "scaling-max-size-a391": "2",
                            "scaling-min-size-a391": "1",
                            "stack-name-a391": "cit-test-stack",
                            "subnets-a391": [
                                "subnet-3bda5d5c",
                                "subnet-43431409"
                            ]
                        }
                    }
                },
                "resource-name": "Amazon EKS Stack",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "cit-test-stack"
# END of BP specific variables


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 720, 10)
    if result != 0:
        raise CloudBoltException(
            "Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress(
        "Blueprint deployment order {} completed successfully.".format(order_id))


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
    test_order_blueprint(client)

    
    resource = bp.resource_set.get(name=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
    ''' we don't have sync functionality 
    # Delete the resource from the database only
    resource.delete()
    set_progress("### DISCOVERING RESOURCES FOR BLUEPRINT ###", tasks_done=1)
    bp.sync_resources()

    # should be able to get the resource since the sync should have created it
    resource = bp.resource_set.get(
        name__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE')
    '''
    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=2)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=3)
