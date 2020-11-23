from common.methods import set_progress
from servicecatalog.models import ServiceBlueprint
from utilities.models import ConnectionInfo
from resources.models import Resource, ResourceType
from infrastructure.models import CustomField

import requests
import json
from ast import literal_eval

BLUEPRINT_ID = 48
API_CLIENT_CI = "Citrix API"
URL = "https://portal.cedexis.com:443/api/v2/config/authdns.json/record"


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='record_id',
        defaults={
            "label": 'Citrix DNS Record ID',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='record_value',
        defaults={
            "label": 'Citrix DNS Record Value',
            "type": 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='ttl',
        defaults={
            "label": 'Citrix DNS Record TTL',
            "type": 'INT',
        }
    )
    CustomField.objects.get_or_create(
        name='recordType',
        defaults={
            "label": 'Citrix DNS Record Type',
            "type": 'STR',
        }
    )


def get_citrix_url():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return "{protocol}://{hostname}".format(protocol=ci.protocol, hostname=ci.ip)


def get_citrix_api_token():
    # Citrix api uses tokens to authorise requests. The tokens expires after a short while and has to be regenerated.
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    url = get_citrix_url()
    response = requests.get(
        "{url}/api/oauth/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials".format(
            url=url, client_id=ci.username, client_secret=ci.password))
    token = response.json().get('access_token')

    return token


def generate_options_for_route53dnsRecord(**kwargs):
    blueprint = ServiceBlueprint.objects.get(id=BLUEPRINT_ID)

    records = []
    for zone in blueprint.resource_set.all():
        if zone.dns_record_type in ['AAAA', 'A', 'MX', 'TXT']:
            records.append(
                ((zone.dns_record_value, zone.dns_record_type), zone.name + " " + zone.dns_record_type + " Record"))
    return records


def generate_options_for_delete_record(**kwargs):
    return [(True, "Yes"), (False, "No")]


def run(resource, *args, **kwargs):
    create_custom_fields()
    route53dnsRecord = "{{ route53dnsRecord }}"
    delete_record = "{{ delete_record }}"

    dns_record_bp = ServiceBlueprint.objects.get(name__iexact='Citrix ITM Records')
    dns_record_resource_type = ResourceType.objects.filter(name__iexact="dns_record").first()

    # Create a new Citrix DNS record
    token = get_citrix_api_token()
    value, recordType = literal_eval(route53dnsRecord)
    ttl = 360
    dnsZone = int(resource.citrix_zone_id)

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the " \
                              "connection info page "
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    for val in literal_eval(value):

        set_progress(f"Checki {dns_record_resource_type}, {resource.group}")
        data = json.dumps({
            "recordType": recordType,
            "quickEdit": True,
            "response": val.get('Value'),
            "ttl": int(ttl),
            "dnsZoneId": dnsZone,
        }
        )
        response = requests.post(url=URL, data=data, headers=head)

        if response.ok:
            record_name = str(dnsZone) + "- " + recordType
            # Create a new DNS Zone record
            set_progress(f"RecordName {record_name}")
            dns_record, _ = Resource.objects.get_or_create(
                name=record_name,
                blueprint=dns_record_bp,
                defaults={
                    "group": resource.group,
                    "resource_type": dns_record_resource_type,
                })
            dns_record.record_id = response.json().get('id')
            dns_record.record_value = {"addresses": list(val.get('Value'))}
            dns_record.name = record_name
            dns_record.lifecycle = 'ACTIVE'
            dns_record.parent_resource = resource
            dns_record.ttl = int(ttl)
            dns_record.recordType = recordType
            dns_record.citrix_zone_id = dnsZone
            dns_record.save()
        else:
            return "FAILURE", f"Record {recordType} with value {val} could not be imported", f"{response.json().get('errorDetails')[0].get('developerMessage')}"
    return "SUCCESS", f"'{recordType}' Value With {value} Added Successfully", ""
