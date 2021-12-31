"""
Plug-in for creating a Google cloud firewall.
"""
from __future__ import unicode_literals

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from infrastructure.models import CustomField, Environment
from resourcehandlers.gcp.models import GCPProject
from common.methods import set_progress
import time, json 

def generate_options_for_env_id(server=None, **kwargs):
    gcp_envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Google Cloud Platform")
    options = []
    for env in gcp_envs:
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

    firewall_name = "{{ firewall_name }}"
    priority = "{{ priority }}"
    direction = "{{ direction }}"
    allowed_ports = "{{ allowed_ports }}"
    allowed_protocol = "{{ allowed_protocol }}"
    generate_custom_fields_as_needed()

    job.set_progress('Connecting to Google Cloud...')

    set_progress("RH: %s" % rh)

    project_id = environment.gcp_project
    gcp_project = GCPProject.objects.get(id=project_id).gcp_id
    
    try:
        account_info = json.loads(rh.gcp_projects.get(id=project_id).service_account_info)
    except Exception:
        account_info = json.loads(rh.gcp_projects.get(id=project_id).service_account_key)

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(account_info)

    job.set_progress(
        "Connecting to Google Cloud through service account email {}".format(
            account_info["client_email"]
        )
    )
    set_progress("RH: %s" % rh)

    service_name = "compute"
    version = "v1"
    client = build(service_name, version, credentials=credentials, cache_discovery = False)
    set_progress("Connection to google cloud established")

    firewall_body = {
        "name": firewall_name,
        "priority": priority,
        "direction": direction,
        "allowed": [
            {
            "IPProtocol": allowed_protocol,
            "ports": allowed_ports.split(','),
            }
        ],
    }
    set_progress('Creating firewall - {} '.format(firewall_name))
    
    try:
        resp = client.firewalls().insert(project=gcp_project, body=firewall_body).execute()
    except Exception as e:
        set_progress("Exception occured while creating the firewall rule in GCP: {}".format(e))
    
    #wait for the firewall to be created
    time.sleep(10)
    
    created_firewall = client.firewalls().get(project=gcp_project, firewall=firewall_name).execute()
    assert created_firewall['name'] == firewall_name

    #save the resource
    resource = kwargs.pop('resources').first()
    resource.google_rh_id = rh.id
    resource.name = firewall_name
    resource.google_firewall_name = firewall_name
    resource.google_firewall_priority = priority
    resource.google_firewall_direction = direction
    resource.google_cloud_project = gcp_project
    resource.save()

    set_progress('Firewall rule has been created')
    return "SUCCESS", "", ""