"""
Plug-in for creating a Google cloud firewall.
"""
from __future__ import unicode_literals
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from infrastructure.models import CustomField, Environment
from common.methods import set_progress
import time, json

def generate_options_for_env_id(server=None, **kwargs):
    gce_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Compute Engine")
    options = []
    for env in gce_envs:
        options.append((env.id, env.name))
    if not options:
        raise RuntimeError("No valid Google Compute Engine resource handlers in CloudBolt")
    return options

def generate_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='google_rh_id',
        defaults={"label":'Google RH ID', "type":'STR',
        "description":'Used by the Google SQL blueprint'}
    )

    CustomField.objects.get_or_create(
        name='google_region',
        defaults={
        "label":'Google region', "type":'STR',
        "description":'Google region'}
    )

    CustomField.objects.get_or_create(
        name='google_firewall_name',
        defaults={
        "label":'Google firewall region', "type":'STR',
        "description":'Google firewall region'}
    )

    CustomField.objects.get_or_create(
        name='google_firewall_priority',
        defaults={
        "label":'Google firewall priority', "type":'STR',
        "description":'Google firewall priority'}
    )

    CustomField.objects.get_or_create(
        name='google_firewall_direction',
        defaults={
        "label":'Google firewall direction', "type":'STR',
        "description":'Google firewall direction'}
    )

    CustomField.objects.get_or_create(
        name='google_cloud_project',
        defaults={
        "label":'Google cloud project', "type":'STR',
        "description":'Google cloud project'}
    )

def generate_options_for_allowed_protocol(server=None, **kwargs):
    return ['tcp', 'udp', 'icmp', 'esp', 'ah', 'ipip', 'sctp']

def generate_options_for_direction(server=None, **kwargs):
    return ['INGRESS', 'EGRESS']

def run(job=None, logger=None, **kwargs):
    environment = Environment.objects.get(id='{{ env_id }}')
    rh = environment.resource_handler.cast()
    region = str(environment.name[:-2])

    firewall_name = "{{ firewall_name }}"
    priority = "{{ priority }}"
    direction = "{{ direction }}"
    allowed_ports = "{{ allowed_ports }}"
    allowed_protocol = "{{ allowed_protocol }}"
    generate_custom_fields_as_needed()

    job.set_progress('Connecting to Google Cloud...')

    set_progress("RH: %s" % rh)

    project = rh.project

    credentials = ServiceAccountCredentials.from_json_keyfile_dict({
        'client_email': rh.serviceaccount,
        'private_key': rh.servicepasswd,
        'type': 'service_account',
        'project_id': project,
        'client_id': None,
        'private_key_id': None,
    })

    client = build('compute', 'v1', credentials=credentials)
    set_progress("Connection to google cloud established")
    set_progress(json.dumps(allowed_ports.split(',')))
    set_progress(type(allowed_ports.split(',')))

    firewall_body = {
        "name": firewall_name,
        "priority": priority,
        "direction": direction,
        "allowed": [
            {
            "IPProtocol": allowed_protocol,
            "ports": json.dumps(allowed_ports.split(','))
            }
        ],
    }

    client.firewalls().insert(project=project, body=firewall_body).execute()

    #wait for the firewall to be created
    time.sleep(10)

    created_firewall = client.firewalls().get(project=project, firewall=firewall_name).execute()
    assert created_firewall['name'] == firewall_name

    #save the resource
    resource = kwargs.pop('resources').first()
    resource.google_rh_id = rh.id
    resource.google_region = region
    resource.name = firewall_name
    resource.google_firewall_name = firewall_name
    resource.google_firewall_priority = priority
    resource.google_firewall_direction = direction
    resource.google_cloud_project = project
    resource.save()

    set_progress('Firewall rule has been created')
