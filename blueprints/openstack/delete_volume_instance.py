import openstack
from openstack import connection
from infrastructure.models import CustomField, Environment
from utilities.models import ConnectionInfo
from resourcehandlers.openstack.models import OpenStackHandler
from common.methods import set_progress
from resources.models import ResourceType, Resource

CONN = ConnectionInfo.objects.get(name='Openstack')
assert isinstance(CONN, ConnectionInfo)

AUTH_URL = '{}://{}:{}/v3'.format(CONN.protocol, CONN.ip, CONN.port)

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


def run(job, **kwargs):
    # resource = job.resource_set.first()
    resource = kwargs.pop('resources').first()

    conn = generate_creds()
    set_progress("Connection to Openstack established")

    name = resource.attributes.get(field__name='server_name').value
    set_progress("Deleting volume instance {}".format(name))

    try:
        conn.delete_server(name_or_id=name)
    except Exception as error:
        return "FAILURE", "", f"{ error }"

    return "SUCCESS", "Server {} deleted".format(name), ""
