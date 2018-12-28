'''
http://boto3.readthedocs.io/en/latest/reference/services/route53.html
http://boto3.readthedocs.io/en/latest/reference/services/route53.html#Route53.Client.change_resource_record_sets
'''
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress


#dns zone friendly name -- no trailing period
ROUTE_53_DNS_DOMAIN = '{{ r53_domain_name }}'

# 'CREATE'|'DELETE'|'UPSERT'
ACTION = '{{ r53_action }}'

# 'SOA'|'A'|'TXT'|'NS'|'CNAME'|'MX'|'NAPTR'|'PTR'|'SRV'|'SPF'|'AAAA'|'CAA'
RECORD_TYPE = 'A'

# 60 | 120 | <any Integer> '
TTL = 300

def get_hosted_zone_id(client=None, zone=None, env_vpc_id=None):
    '''
     This code is intended to work out issues where multiple DNS zones are named
        the same but assigned to different VPCs, and with this logic we can
        determine the correct domain name based on the vpc_id from the server
        environment (if there are multiple domains named the same), otherwise
        (if there is only 1 domain found), then it doesnt go to that level of
        integrity checking.

        updated 2018/12/20
    '''

    #set_progress(f'getting zone: {zone}')
    zone_name = f'{zone}.' #zone names have a trailing period
    response = client.list_hosted_zones_by_name(DNSName=zone_name)

    #set_progress(f"LEN = {len(response['HostedZones'])}")

    if len(response['HostedZones']) == 1:
        return response['HostedZones'][0]['Id']
    elif len(response['HostedZones']) > 1:
        for dns_zone in response['HostedZones']:
            #set_progress(dns_zone['Id'], ' -- ', dns_zone['Name'])
            hz = client.get_hosted_zone(Id=dns_zone['Id'])
            if not hz:
                #set_progress(f"ERROR GETTING HOSTED ZONE FROM AWS: {Item['Id']}")
                break
            if env_vpc_id == hz['VPCs'][0]['VPCId']:
                #set_progress(f"returning: {dns_zone['Id']}")
                return dns_zone['Id']

    #set_progress('returning: False')
    return False

#needed more resiliency in this function - see above
#def get_hosted_zone_id(client, zone):
#    response = client.list_hosted_zones_by_name(DNSName=zone)
#    # get first hosted zone returned
#    hosted_zone = response['HostedZones'][0]
#    zone_id = hosted_zone['Id']
#    return zone_id


def change_resource_record(client, zone_id, batch):
    '''
        perform the update on the record in the given zone id based on the batch
        information
    '''
    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=batch
    )
    return response


def run(job=None, server=None, **kwargs):
    '''
        update the route 53 dns record
    '''
    route_53_dns_zone = ROUTE_53_DNS_DOMAIN
    nic = server.nics.first()
    dns_domain = nic.network.dns_domain
    if not dns_domain:
        msg = 'DNS domain not set on selected NIC: {}'.format(nic)
        return "FAILURE", "", msg
    rh = server.resource_handler.cast()
    if not isinstance(rh, AWSHandler):
        msg = 'Route53 not supported on RH Type: {}'.format(rh)
        return "FAILURE", "", msg

    region = server.environment.get_cfv('aws_region')
    client = rh.get_boto3_client(region_name=region, service_name='route53')

    zone_id = get_hosted_zone_id(client=client,
                                 zone=route_53_dns_zone,
                                 env_vpc_id=server.environment.vpc_id)
    name = f'{server.hostname}.{dns_domain}'
    #name = '{}.{}'.format(server.hostname, dns_domain)

    batch = {
        'Comment': 'Created by CloudBolt Job ID: {}'.format(job.id),
        'Changes': [
            {
                'Action': ACTION,
                'ResourceRecordSet': {
                    'ResourceRecords': [{'Value': server.ip}],
                    'Name': name,
                    'Type': RECORD_TYPE,
                    'TTL': TTL
                }
            },
        ]
    }

    change_resource_record(client=client, zone_id=zone_id, batch=batch)

    return "SUCCESS", "", ""
