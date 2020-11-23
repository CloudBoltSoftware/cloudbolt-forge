from common.methods import set_progress
from utilities.models import ConnectionInfo
from servicecatalog.models import ServiceBlueprint
from infrastructure.models import CustomField

import json
import requests

API_CLIENT_CI = "Citrix API"


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


def generate_options_for_dnsZone(**kwargs):
    token = get_citrix_api_token()
    url = get_citrix_url() + "/api/v2/config/authdns.json"
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    domains = requests.get(url=url, headers=head).json()

    return [(domain.get('id'), domain.get('domainName')) for domain in domains]


def generate_options_for_recordType(**kwargs):
    return ["A", "AAAA", "NS", "MX", "TXT"]


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

def run(resource, *args, **kwargs):
    create_custom_fields()

    url = "https://portal.cedexis.com:443/api/v2/config/authdns.json/record"
    token = get_citrix_api_token()
    value = "{{ value }}"
    ttl = "{{ ttl }}" or 300
    dnsZone = "{{ dnsZone }}"
    recordType = "{{ recordType }}"

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the " \
                              "connection info page "
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    data = json.dumps({
        "recordType": recordType,
        "quickEdit": True,
        "response": value,
        "ttl": int(ttl),
        "dnsZoneId": int(dnsZone),
    }
    )
    response = requests.post(url=url, data=data, headers=head)
    bp = ServiceBlueprint.objects.get(name='Citrix ITM Zone')
    zone = [res for res in bp.resource_set.all() if res.citrix_zone_id == dnsZone]
    if response.ok:
        if zone:
            citrix_zone = zone[0]
            resource.name = '{}- {}'.format(dnsZone, recordType)
            resource.parent_resource = citrix_zone
            resource.record_id = response.json().get('id')
            resource.citrix_zone_id = response.json().get('dnsZoneId')
            resource.recordType = response.json().get('recordType')
            resource.record_value = {"addresses": [value]}
            resource.ttl = int(ttl)
            resource.save()
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "", "{}".format(response.json().get('errorDetails')[0].get('developerMessage'))
