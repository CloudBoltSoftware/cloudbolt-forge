from utilities.models import ConnectionInfo
from resources.models import Resource, ResourceType
from accounts.models import Group
from servicecatalog.models import ServiceBlueprint
from infrastructure.models import CustomField

import requests

API_CLIENT_CI = "Citrix API"

RESOURCE_IDENTIFIER = 'domainName'


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
        f"{url}/api/oauth/token?client_id={ci.username}&client_secret={ci.password}&grant_type=client_credentials")
    token = response.json().get('access_token')

    return token


def discover_resources(**kwargs):
    create_custom_fields_as_needed()

    url = get_citrix_url() + "/api/v2/config/authdns.json"
    token = get_citrix_api_token()

    bp = ServiceBlueprint.objects.get(name__iexact='Citrix ITM Zone')
    group = Group.objects.filter(name__icontains='unassigned').first()
    resource_type = ResourceType.objects.get(name__iexact="dns_zone")
    dns_record_bp = ServiceBlueprint.objects.get(name__iexact='Citrix ITM Records')
    dns_record_resource_type = ResourceType.objects.get(name__iexact="dns_record")

    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    domains = requests.get(url=url, headers=head).json()
    """
    Right now, we don't have a way to associate a DNS record to a DNS Zone.
    We thus we have to manually do the association.
    We do this be setting the parent resource of a DNS record as a DNS Zone
    Returning just a list won't get the work done for now.
    """
    for domain in domains:

        dns_zone, _ = Resource.objects.get_or_create(
            name=domain.get('domainName'),
            blueprint=bp,
            defaults={
                "group": group,
                "resource_type": resource_type,
            }
        )
        dns_zone.domainName = domain.get('domainName')
        dns_zone.citrix_zone_id = domain.get('id')
        dns_zone.lifecycle = 'ACTIVE'
        dns_zone.save()

        # Discover all DNS records in a DNS zone

        for record in domain.get('records'):
            record_name = str(record.get('dnsZoneId')) + "- " + record.get('recordType')

            dns_record, _ = Resource.objects.get_or_create(
                name=record_name,
                blueprint=dns_record_bp,
                defaults={
                    "group": group,
                    "resource_type": dns_record_resource_type,
                }
            )
            dns_record.name = record_name
            dns_record.lifecycle = 'ACTIVE'
            dns_record.parent_resource = dns_zone
            dns_record.record_id = record.get('id')
            dns_record.citrix_zone_id = record.get('dnsZoneId')
            dns_record.recordType = record.get('recordType')
            dns_record.record_value = record.get('response')
            dns_record.ttl = record.get('ttl')
            dns_record.save()

    return []
