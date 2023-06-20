from common.methods import set_progress
from infrastructure.models import CustomField
from resourcehandlers.aws.models import AWSHandler

import json


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='zone_id', type='STR', defaults={
            'label': 'AWS Route53 ZoneId',
            'description': 'Used by the AWS blueprints',
            'show_as_attribute': True
        }
    )
    CustomField.objects.get_or_create(
        name='dns_record_type', type='STR', defaults={
            'label': 'DNS Record Type',
            'description': 'Used by the DNS Record Blueprints',
            'show_as_attribute': True
        }
    )
    CustomField.objects.get_or_create(
        name='dns_record_value', type='TXT', defaults={
            'label': 'DNS Record Value(s)',
            'description': 'Used by the DNS Record Blueprints',
            'show_as_attribute': True
        }

    )
    CustomField.objects.get_or_create(
        name='dns_record_ttl', type='INT', defaults={
            'label': 'DNS Record TTL',
            'description': 'Time To Live (in secodns). Used by the DNS Record Blueprints',
            'show_as_attribute': True
        }
    )


def get_route_53_client(aws_id):
    rh = AWSHandler.objects.get(id=aws_id)
    try:
        wrapper = rh.get_api_wrapper()
    except Exception:
        return

    # See http://boto3.readthedocs.io/en/latest/guide/configuration.html#method-parameters
    client = wrapper.get_boto3_client(
        'route53',
        rh.serviceaccount,
        rh.servicepasswd,
        None
    )
    return client


def generate_options_for_aws_id(**kwargs):
    rhs = AWSHandler.objects.all().values("id", "name")
    options = [(rh['id'], rh['name']) for rh in rhs]
    return options


def generate_options_for_zone_id(control_value=None, **kwargs):
    options = []
    if control_value:
        client = get_route_53_client(control_value)
        if not client:
            return []
        zones = client.list_hosted_zones()['HostedZones']

        for z in zones:
            id = z.get('Id').replace('/hostedzone/', '')
            name = z['Name']
            options.append((id, name))
    return options


def generate_options_for_record_type(**kwargs):
    # return ['SOA', 'A', 'TXT', 'NS', 'CNAME', 'MX', 'NAPTR', 'PTR', 'SRV', 'SPF', 'AAAA', 'CAA']
    return [
        ('A', 'A - IPv4 Host Address'),
        ('NS', 'NS - Name Server'),
        ('CNAME', 'CNAME - Canonical Name for an Alias'),
        ('MX', 'MX - Mail eXchange'),
        ('AAAA', 'AAAA - IPv6 Host Address'),
        ('SOA', 'SOA - Start Of Authority'),
    ]


def run(job, *args, **kwargs):

    create_custom_fields_as_needed()

    aws_id = '{{ aws_id }}'
    zone_id = '{{ zone_id }}'
    RECORDSET_NAME = '{{ r53_recordset_name }}'
    RECORD_TYPE = '{{ record_type }}'
    TTL = int('{{ ttl }}')

    if RECORD_TYPE == 'A':
        VALUE = '{{ a_value }}'
    elif RECORD_TYPE == 'AAAA':
        VALUE = '{{ aaaa_value }}'
    elif RECORD_TYPE == 'CNAME':
        VALUE = '{{ cname_value}}'
    elif RECORD_TYPE == 'MX':
        VALUE = '{{ mx_value }}'
    elif RECORD_TYPE == 'NS':
        VALUE = '{{ ns_value }}'
    else:
        VALUE = '{{ soa_value }}'

    set_progress('Connecting to AWS...')

    client = get_route_53_client(aws_id)
    
    set_progress("Creating AWS Route53 DNS RecordSet")

    batch = {
        'Comment': 'Created by CloudBolt Job ID: {}'.format(job.id),
        'Changes': [
            {
                'Action': "CREATE",
                'ResourceRecordSet': {
                    'ResourceRecords': [{'Value': VALUE}],
                    'Name': RECORDSET_NAME,
                    'Type': RECORD_TYPE,
                    'TTL': TTL
                }
            },
        ]
    }

    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=batch
    )

    # fetch the record to make sure it worked
    record = client.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName=RECORDSET_NAME, StartRecordType=RECORD_TYPE, MaxItems='1'
    )['ResourceRecordSets'][0]
    resource = kwargs.pop('resources').first()
    resource.name = RECORDSET_NAME
    resource.zone_id = zone_id
    resource.dns_record_ttl = int(TTL)
    resource.dns_record_value = json.dumps(record['ResourceRecords'])
    resource.dns_record_type = RECORD_TYPE
    resource.aws_rh_id = aws_id

    resource.save()

    return "SUCCESS", "", ""
