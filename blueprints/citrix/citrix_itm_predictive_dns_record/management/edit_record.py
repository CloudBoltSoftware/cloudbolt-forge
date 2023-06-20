from common.methods import set_progress
from utilities.models import ConnectionInfo
from servicecatalog.models import ServiceBlueprint
from infrastructure.models import CustomField

import json
from ast import literal_eval
import requests

API_CLIENT_CI = "Citrix API"


def create_custom_fields_as_needed():
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


def generate_options_for_recordType(**kwargs):
    return ["A", "AAAA", "MX"]


def generate_options_for_editRecordType(**kwargs):
    return [(True, "Yes"), (False, "No")]


def generate_options_for_editRecordValue(**kwargs):
    return [(True, "Yes"), (False, "No")]


def generate_options_for_editTTL(**kwargs):
    return [(True, "Yes"), (False, "No")]


# Need a way to return a string instead of a list.

# def generate_options_for_value(**kwargs):
#     resource = kwargs.get('resource')
#     return literal_eval(resource.record_value).get('addresses')

def run(resource, *args, **kwargs):
    create_custom_fields_as_needed()
    addresses = literal_eval(resource.record_value).get('addresses')
    set_progress(f"Addresses {addresses}")

    _value = "".join(addresses)
    url = f"https://portal.cedexis.com:443/api/v2/config/authdns.json/record/{resource.record_id}"
    token = get_citrix_api_token()
    editRecordValue = "{{ editRecordValue }}"
    val = "{{ value }}"
    value = val or _value

    editTTL = "{{ editTTL }}"
    ttl = "{{ ttl }}" or resource.ttl
    editRecordType = "{{ editRecordType }}"
    recordType = "{{ recordType }}" or resource.recordType
    dnsZone = resource.citrix_zone_id

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the " \
                              "connection info page "
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    data = json.dumps({
        "recordType": recordType,
        "quickEdit": True,
        "response": value,
        "ttl": ttl,
        "dnsZoneId": dnsZone,
        "id": resource.record_id
    }
    )

    response = requests.put(url=url, data=data, headers=head)

    bp = ServiceBlueprint.objects.get(name='Citrix ITM Zone')
    zone = [res for res in bp.resource_set.all() if res.citrix_zone_id == dnsZone]

    if response.ok:
        if val:
            value = {"addresses": [val]}

        resource.name = '{}- {}'.format(dnsZone, recordType)
        resource.parent_resource = zone[0]
        resource.record_id = response.json().get('id')
        resource.record_value = value
        resource.citrix_zone_id = response.json().get('dnsZoneId')
        resource.recordType = recordType
        resource.ttl = int(ttl)
        resource.save()
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "", "{}".format(response.json().get('errorDetails')[0].get('developerMessage'))
