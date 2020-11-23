from common.methods import set_progress
from utilities.models import ConnectionInfo
from infrastructure.models import CustomField

import requests
import json

API_CLIENT_CI = "Citrix API"


def get_citrix_url():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return f"{ci.protocol}://{ci.ip}"


def get_citrix_api_token():
    # Citrix api uses tokens to authorise requests. The tokens expires after a short while and has to be regenerated.
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    url = get_citrix_url()
    response = requests.get(
        f"{url}/api/oauth/token?client_id={ci.username}&client_secret={ci.password}&grant_type=client_credentials")
    token = response.json().get('access_token')

    return token


def generate_options_for_zoneTransferEnabled(**kwargs):
    return [True, False]


def generate_options_for_isPrimary(**kwargs):
    return [True, False]


def generate_options_for_dnsTypeConfig(**kwargs):
    return ["Primary", "Secondary"]


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='domainName', defaults={
            'label': 'Citrix Domain Name', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='citrix_zone_id', defaults={
            'label': 'Citrix Zone ID', 'type': 'STR',
        }
    )


def run(resource, *args, **kwargs):
    create_custom_fields_as_needed()

    domainName = "{{ domainName }}"
    set_progress("Getting Authorization Token.")
    token = get_citrix_api_token()

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the connection info page"

    url = get_citrix_url() + "/api/v2/config/authdns.json"

    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    data = json.dumps({
        "zoneTransferEnabled": "false",
        "isPrimary": "true",
        "domainName": domainName
    })

    response = requests.post(url=url, data=data, headers=head)

    if response.ok:
        domains = requests.get(url=url, headers=head).json()
        result = [domain for domain in domains if domain.get('domainName') == domainName]

        resource.citrix_zone_id = result[0].get('id')
        resource.name = domainName
        resource.domainName = domainName
        resource.save()
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "Sample output message", "{}".format(response.content)


# Just to get the action inputs to show up
_ = "{{ dnsTypeConfig }}"
_ = "{{ zoneTransferEnabled }}"
_ = "{{ isPrimary }}"
