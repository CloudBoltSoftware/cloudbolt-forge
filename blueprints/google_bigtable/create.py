"""
Plug-in for creating a Google Bigtable database.
"""
from __future__ import unicode_literals
import json
import time
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from orders.models import CustomFieldValue
from resourcehandlers.gcp.models import GCPHandler, GCPProject

INSTANCE_TYPE = "PRODUCTION"  # "DEVELOPMENT" is permitted, but deprecated


def generate_options_for_env_id(server=None, **kwargs):
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    options = []
    for env in gcp_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError("No valid Google Cloud Platform resource handlers in CloudBolt")
    return options


def generate_options_for_zone(server=None, control_value=None, **kwargs):
    if not control_value:
        return []
    env = Environment.objects.get(id=control_value)
    options = []
    gcp_zone_cf = CustomField.objects.get(name="gcp_zone")

    configured_zones = env.custom_field_options.filter(field=gcp_zone_cf)
    for location in configured_zones:
        options.append((location.id, location.str_value))
    if not options:
        raise RuntimeError("Failed to load Google Cloud zone options")
    return options


def create_bigtable_api_wrapper(gcp_handler: GCPHandler) -> Resource:
    """
    Using googleapiclient.discovery, build the api wrapper for the bigtableadmin api:
    https://googleapis.github.io/google-api-python-client/docs/dyn/bigtableadmin_v2.projects.instances.html
    """
    if not gcp_handler.gcp_api_credentials:
        set_progress("Could not find Google Cloud credentials for this reource handler.")
        return None
    credentials_dict = json.loads(gcp_handler.gcp_api_credentials)
    credentials = Credentials(**credentials_dict)
    bigtable_wrapper: Resource = build("bigtableadmin", "v2", credentials=credentials, cache_discovery=False)
    return bigtable_wrapper


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='google_rh_id', defaults={'label': 'Google RH ID', 'type': 'STR',
                                       'description': 'Used by the Google SQL blueprint'}
    )

    CustomField.objects.get_or_create(
        name='instance_name', defaults={'label': 'Google instance identifier', 'type': 'STR',
                                        'description': 'Used by the Google Cloud SQL blueprint'}
    )

    CustomField.objects.get_or_create(
        name='project_id', defaults={'label': 'Google Cloud project', 'type': 'STR',
                                        'description': 'Used by the Google Cloud SQL blueprint'}
    )


def create_bigtable(
    wrapper: Resource, project_id: str, instance_id: str, cluster_id, instance_type: str, location: str, serve_nodes: int
) -> dict:
    """
    Create a bigtable instance (many other aspects can be specified - see api docs for details)
    https://cloud.google.com/bigtable/docs/reference/admin/rest/v2/projects.instances/create
    """

    proj_str = f"projects/{project_id}"
    location_str = f"{proj_str}/locations/{location}"

    table_create_body = {"instanceId": instance_id, "instance": {"displayName": instance_id, "type": instance_type, "labels": {"createdby": "cmp"}}, "clusters": { cluster_id: {"location": location_str, "serveNodes": serve_nodes}}}
    create_request = wrapper.projects().instances().create(parent=proj_str, body=table_create_body)  

    create_operation = create_request.execute()
    return create_operation


def get_operation_status(wrapper: Resource, operation_name: str) -> bool:
    """
    Used to poll for the status of a running operation
    https://cloud.google.com/bigtable/docs/reference/admin/rest/v2/operations/get
    """
    ops_request = wrapper.operations().get(name=operation_name)
    op = ops_request.execute()
    return op.get('done', False) # True when the operation has completed


def run(job=None, logger=None, **kwargs):
    create_custom_fields_as_needed()
    instance_id = '{{ db_identifier }}'
    serve_nodes = 3
    zone_cfv_id = '{{ zone }}'
    zone_cfv = CustomFieldValue.objects.get(id=zone_cfv_id)
    location_id = zone_cfv.str_value
    set_progress("Instance ID will be: %s" % instance_id)
    assert 6 <= len(instance_id) <= 33

    environment = Environment.objects.get(id='{{ env_id }}')
    project_id = environment.gcp_project
    gcp_project_name = GCPProject.objects.get(id=project_id).gcp_id
    rh = environment.resource_handler.cast()
    set_progress("RH: %s" % rh)
    set_progress('location_id: %s' % location_id)

    resource = kwargs.pop('resources').first()
    resource.name = instance_id
    resource.instance_name = instance_id
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.google_rh_id = rh.id
    # store the GCP project_id on the resource for passing to the delete API
    resource.project_id = gcp_project_name
    resource.save()

    set_progress("instance type: %s" % INSTANCE_TYPE)

    job.set_progress('Connecting to Google Cloud...')
    wrapper = create_bigtable_api_wrapper(rh)
    set_progress("Connection established")

    # NOTE: default_storage_type can be used to determine SSD vs SHD.
    cluster_id = instance_id + '-1'
    set_progress('Cluster ID: %s (will serve %i nodes)' % (cluster_id, serve_nodes))

    set_progress("\nCreating instance and cluster...")

    operation = create_bigtable(wrapper, gcp_project_name, instance_id, cluster_id, INSTANCE_TYPE, location=location_id, serve_nodes=serve_nodes)  

    while not get_operation_status(wrapper, operation['name']):
        set_progress("Waiting for instance creation to finish...")
        time.sleep(2.0)
    set_progress("Instance %s created" % instance_id)