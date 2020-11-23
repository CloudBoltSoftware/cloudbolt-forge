"""
Plug-in for creating a Google Bigtable database.
"""
from __future__ import unicode_literals
from infrastructure.models import CustomField, Environment
from common.methods import set_progress
import json, tempfile
from google.cloud import bigtable
import os
import time


def generate_options_for_env_id(server=None, **kwargs):
    gce_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Compute Engine")
    options = []
    for env in gce_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError("No valid Google Compute Engine resource handlers in CloudBolt")
    return options


def generate_options_for_instance_type(server=None, **kwargs):
    return [
        (int(bigtable.enums.Instance.Type.PRODUCTION), 'Production'),
        (int(bigtable.enums.Instance.Type.DEVELOPMENT), 'Development'),
    ]


def create_client(rh):
    json_fd, json_path = tempfile.mkstemp()

    json_dict = {'client_email': rh.serviceaccount,
                 'token_uri': 'https://www.googleapis.com/oauth2/v4/token',
                 'private_key': rh.servicepasswd
                 }

    with open(json_path, 'w') as fh:
        json.dump(json_dict, fh)

    client = bigtable.client.Client.from_service_account_json(json_path,
                                                              admin=True, project=rh.project)

    os.close(json_fd)
    return client


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='google_rh_id', defaults={'label': 'Google RH ID', 'type': 'STR',
                                       'description': 'Used by the Google SQL blueprint'}
    )

    CustomField.objects.get_or_create(
        name='instance_name', defaults={'label': 'Google instance identifier', 'type': 'STR',
                                        'description': 'Used by the Google Cloud SQL blueprint'}
    )


def run(job=None, logger=None, **kwargs):
    create_custom_fields_as_needed()
    instance_type = int('{{ instance_type }}')
    instance_id = '{{ db_identifier }}'
    set_progress("Instance ID will be: %s" % instance_id)
    assert 6 <= len(instance_id) <= 33

    environment = Environment.objects.get(id='{{ env_id }}')
    rh = environment.resource_handler.cast()
    location_id = str(environment.node_location)
    set_progress("RH: %s" % rh)
    set_progress('location_id: %s' % location_id)

    resource = kwargs.pop('resources').first()
    resource.name = instance_id
    resource.instance_name = instance_id
    # Store the resource handler's ID on this resource so the teardown action
    # knows which credentials to use.
    resource.google_rh_id = rh.id
    resource.save()

    set_progress("instance type: %s" % instance_type)

    job.set_progress('Connecting to Google Cloud...')
    client = create_client(rh)
    set_progress("Connection established")

    if instance_type == int(bigtable.enums.Instance.Type.DEVELOPMENT):
        # For development instance types, clusters do not have nodes in them:
        serve_nodes = 0
    else:
        # Production instance clusters can have 3 or more nodes each:
        # In the future we could allow the user to customize this.
        serve_nodes = 3

    # NOTE: default_storage_type can be used to determine SSD vs SHD.
    cluster_id = instance_id + '-1'
    set_progress('Cluster ID: %s (will serve %i nodes)' % (cluster_id, serve_nodes))

    set_progress("\nCreating instance and cluster...")
    instance = client.instance(instance_id, display_name=instance_id, instance_type=instance_type)

    cluster = bigtable.cluster.Cluster(instance=instance, cluster_id=cluster_id, location_id=location_id,
                                       serve_nodes=serve_nodes)

    # NOTE: this call can also automatically create clusters, if instead of
    # clusters, we pass in location_id, serve_nodes, and default_storage_type.
    operation = instance.create(clusters=[cluster])
    # NOTE: Above will raise AlreadyExists exception, which would be displayed
    # to the user in CB, if the instance with this name already exists.

    while not operation.done():
        set_progress("Waiting for instance creation to finish...")
        time.sleep(2.0)
    set_progress("Instance %s created" % instance_id)
