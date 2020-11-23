import json
import logging
import re

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo

from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources.models import ResourceGroup
from infrastructure.models import CustomField, Environment

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

API_CLIENT_CI = "CIT API Client"

# BP specific variables - You should change these
BLUEPRINT = 106

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/106/",
                "blueprint-items-arguments": {
                    "build-item-Create Azure Kubernetes Service": {
                        "parameters": {
                            "cloudbolt-environment-a493": "89",
                            "cluster-dns-prefix-a493": "citdnsprefix",
                            "cluster-name-a493": "CITclustertest",
                            "cluster-pool-name-a493": "cittpool1",
                            "node-count-a493": "2",
                            "resource-groups-a493": "CITResourceGroup"
                        }
                    }
                },
                "resource-name": "Azure Kubernetes",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = 'CITclusterDontdelete'

def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 1800, 10)
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress("Blueprint deployment order {} completed successfully.".format(order_id))


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
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=2)
    test_order_blueprint(client)

    resource = bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE').first()

    set_progress("RESOURCE {}".format(resource))
    rce = bp.resource_set.last()
    set_progress("LAST RESOURCE {}".format(rce))
    resource.delete()

    set_progress('### DISCOVERING RESOURCES FOR BLUEPRINT ###', tasks_done=1)
    bp.sync_resources()

    # Should be able to get the resource since the sync should have created it.
    resource = bp.resource_set.get(nam__icontains=NEW_RESOURCE_NAME, lifecycle='ACTIVE')

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=1)
    test_delete_resource(client, resource)

    set_progress("ALL Tests completed!", tasks_done=2)
