from common.methods import set_progress
from utilities.models import ConnectionInfo
from infrastructure.models import CustomField
from resources.models import Resource, ResourceType
from servicecatalog.models import ServiceBlueprint

import requests
import json

API_CLIENT_CI = "Cedexis API"


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='newsletter', defaults={
            'label': 'Citrix Account newsletter', 'type': 'BOOL',
        }
    )
    CustomField.objects.get_or_create(
        name='billingContact', defaults={
            'label': 'Citrix Account billingContact', 'type': 'BOOL',
        }
    )
    CustomField.objects.get_or_create(
        name='businessContact', defaults={
            'label': 'Citrix Account businessContact', 'type': 'BOOL',
        }
    )
    CustomField.objects.get_or_create(
        name='technicalContact', defaults={
            'label': 'Citrix Account technicalContact', 'type': 'BOOL',
        }
    )

    CustomField.objects.get_or_create(
        name='firstName', defaults={
            'label': 'Citrix Account firstname', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='lastName', defaults={
            'label': 'Citrix Account lastname', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='country', defaults={
            'label': 'Citrix Account country', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='phone', defaults={
            'label': 'Citrix Account phone', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='apiClientId', defaults={
            'label': 'Citrix Account apiClientId', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='company', defaults={
            'label': 'Citrix Account company', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='email', defaults={
            'label': 'Citrix Account email', 'type': 'STR',
        }
    )


def get_cedexis_url():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return f"{ci.protocol}://{ci.ip}"


def get_cedexis_api_token():
    # Cedexis api uses tokens to authorise requests. The tokens expires after a short while and has to be regenerated.
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    url = get_cedexis_url()
    response = requests.get(
        f"{url}/api/oauth/token?client_id={ci.username}&client_secret={ci.password}&grant_type=client_credentials")
    token = response.json().get('access_token')

    return token


def run(resource, *args, **kwargs):
    blueprint = ServiceBlueprint.objects.get(name__iexact='Citrix ITM Account')
    resource_type = ResourceType.objects.get(name__iexact='Accounts')

    create_custom_fields_as_needed()

    firstName = "{{ firstName }}"
    lastName = "{{ lastName }}"
    country = "{{ country }}"
    phone = "{{ phone }}"
    company = "{{ company }}"
    email = "{{ email }}"
    apiClientId = "{{ apiClientId }}"

    token = get_cedexis_api_token()

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the " \
                              "connection info page "

    url = get_cedexis_url() + "/api/v2/config/accounts.json"

    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    data = json.dumps({
        "newsletter": False,
        "firstName": firstName,
        "lastName": lastName,
        "country": country,
        "billingContact": False,
        "phone": phone,
        "businessContact": False,
        "apiClientId": apiClientId,
        "company": company,
        "technicalContact": False,
        "email": email
    })

    response = requests.post(url=url, data=data, headers=head)
    set_progress(response.content)

    if response.ok:
        account_resource, _ = Resource.objects.get_or_create(
            name=email,
            blueprint=blueprint,
            defaults={
                'group': resource.group,
                'lifecycle': 'Active',
                'resource_type': resource_type})

        account_resource.firstName = firstName
        account_resource.newsletter = False
        account_resource.lastName = lastName
        account_resource.country = country
        account_resource.billingContact = False
        account_resource.phone = phone
        account_resource.businessContact = False
        account_resource.apiClientId = apiClientId
        account_resource.company = company
        account_resource.technicalContact = False
        account_resource.email = email

        account_resource.save()

        return "SUCCESS", "", ""
    else:
        return "FAILURE", "", "{}".format(response.content)
