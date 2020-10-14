import json
import logging
import re
import time

from api.api_samples.python_client.api_client import CloudBoltAPIClient
from api.api_samples.python_client.samples.api_helpers import wait_for_order_completion
from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.exceptions import CloudBoltException
from utilities.models import ConnectionInfo
from infrastructure.models import CustomField, Environment
from utilities.models import ConnectionInfo
from resourcehandlers.openstack.models import OpenStackHandler
from common.methods import set_progress
from resources.models import ResourceType, Resource

# suppress logging from requests module
logger = logging.getLogger('requests')
logger.setLevel(40)
logger = logging.getLogger('py.warnings')
logger.setLevel(40)

CONN = ConnectionInfo.objects.get(name='Openstack')
assert isinstance(CONN, ConnectionInfo)

AUTH_URL = '{}://{}:{}/v3'.format(CONN.protocol, CONN.ip, CONN.port)

API_CLIENT_CI = "CIT API Client"

BLUEPRINT = 83

BP_PAYLOAD = """
{
    "group": "/api/v2/groups/2/",
    "items": {
        "deploy-items": [
            {
                "blueprint": "/api/v2/blueprints/83/",
                "blueprint-items-arguments": {
                    "build-item-Boot Instance from Volume": {
                        "parameters": {
                            "availability-zone-a376": "nova",
                            "cloudbolt-environment-a376": "132",
                            "flavor-a376": "m1.tiny",
                            "floating-ips-a376": "172.24.4.2",
                            "hostname-a376": "Openstack_boot_cit19",
                            "key-pair-name-a376": "mykey",
                            "network-a376": "priv-net1",
                            "security-group-a376": "default",
                            "volume-a376": "test_vol2_do_not_use"
                        }
                    }
                },
                "resource-name": "Openstack Boot Volume",
                "resource-parameters": {}
            }
        ]
    },
    "submit-now": "true"
}
"""

NEW_RESOURCE_NAME = "Openstack_boot_cit19"


def get_order_id_from_href(order_href):
    mo = re.search("/orders/([0-9]+)", order_href)
    return int(mo.groups()[0])


def test_order_blueprint(client):
    order = json.loads(client.post('/api/v2/orders/', body=BP_PAYLOAD))
    order_href = order['_links']['self']['href']
    order_id = get_order_id_from_href(order_href)
    result = wait_for_order_completion(client, order_id, 900, 10)
    if result != 0:
        raise CloudBoltException("Blueprint Deployment order {} did not succeed.".format(order_id))
    set_progress("Blueprint deployment order {} completed successfully.".format(order_id))

def test_delete_resource(client,resource):
    body = "{}"
    delete = json.loads(client.post(
        '/api/v2/resources/{}/{}/actions/1/'.format(resource.resource_type.name, resource.id), body=body))

def generate_creds():
    rh = OpenStackHandler.objects.first()
    conn = connection.Connection(
       region_name='RegionOne',
       auth=dict(auth_url= AUTH_URL,
       username=rh.serviceaccount, password=rh.servicepasswd,
       project_id=rh.project_id,
       user_domain_id=rh.domain),
       compute_api_version='2.1', identity_interface='public', verify=False)
    return conn

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
    set_progress("### ORDERING BLUEPRINT ###", tasks_done=0, total_tasks=1)
    test_order_blueprint(client)

    resource = bp.resource_set.filter(
        name__iexact=NEW_RESOURCE_NAME, lifecycle='ACTIVE').first()

    set_progress(f"RESOURCE {resource}")
    rce = bp.resource_set.filter(name__iexact=NEW_RESOURCE_NAME).first()
    set_progress(f"LAST RESOURCE {rce}")

    set_progress("### DELETING RESOURCE FOR BLUEPRINT ###", tasks_done=1)
    test_delete_resource(client,resource)

    set_progress("ALL Tests completed!", tasks_done=1)

