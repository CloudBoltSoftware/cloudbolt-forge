"""
SolarWinds IPAM
Add Node and Pollers
IV. Pre-Create Resource
"""
if __name__ == '__main__':
    import os
    import sys
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.append('/opt/cloudbolt')
    django.setup()

import re
import orionsdk
import requests
from common.methods import set_progress
from jobs.models import Job
from utilities.models import ConnectionInfo
from orionsdk import SwisClient

def run(job=None, *args, **kwargs):
    # Disable SSL warnings
    verify = False
    if not verify:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Get SolarWinds ConnectionInfo
    solarwinds = ConnectionInfo.objects.get(name='SolarWinds')
    swis = SwisClient(solarwinds.ip, solarwinds.username, solarwinds.password)
    if not solarwinds:
        return "FAILURE", "", "Missing required SolarWinds connection info. (Admin -> Connection Info -> New Connection Info)"

    # Get Server
    server = job.server_set.first()

    # Get subnet server.ip
    sep = '.'
    octets = server.ip.split(sep='.')
    network = sep.join(octets[:3] + list('0'))

    # Get next available IP from SW based on subnet
    next_ip = swis.query("SELECT TOP 1 I.Status, I.DisplayName FROM IPAM.IPNode I WHERE Status=2 AND I.Subnet.Address = '{}'".format(network))

    # Set the server ip
    server.ip = next_ip['results'][0]['DisplayName']
    server.save()

    # Setup Node Properties
    props = {
        'IPAddress': server.ip,
        'EngineID': 1,
        'ObjectSubType': 'Agent',
        'Caption': server.hostname,
        'DNS': server.hostname,
        'Description': 'Added by CloudBolt',
        'Contact': server.owner,
        }

    #Create the Node
    job.set_progress("Adding '{}' to SolarWinds".format(server.hostname))
    results = swis.create('Orion.Nodes', **props)

    # Extract NodeID from results
    nodeid = re.search('(\d+)$', results).group(0)

    # Setup Poller Status for the node
    pollers_enabled = {
        'N.Status.ICMP.Native': True,
        'N.Status.SNMP.Native': False,
        'N.ResponseTime.ICMP.Native': True,
        'N.ResponseTime.SNMP.Native': False,
        'N.Details.SNMP.Generic': True,
        'N.Uptime.SNMP.Generic': True,
        'N.Cpu.SNMP.HrProcessorLoad': True,
        'N.Memory.SNMP.NetSnmpReal': True,
        'N.AssetInventory.Snmp.Generic': True,
        'N.Topology_Layer3.SNMP.ipNetToMedia': False,
        'N.Routing.SNMP.Ipv4CidrRoutingTable': False
    }
    # Add Node to Pollers
    pollers = []
    for k in pollers_enabled:
        pollers.append(
            {
                'PollerType': k,
                'NetObject': 'N:' + nodeid,
                'NetObjectType': 'N',
                'NetObjectID': nodeid,
                'Enabled': pollers_enabled[k]
            }
        )

    for poller in pollers:
        job.set_progress("Adding poller type: '{}' with status {}...".format(poller['PollerType'], poller['Enabled']))
        response = swis.create('Orion.Pollers', **poller)

    #Poll the node
    swis.invoke('Orion.Nodes', 'PollNow', 'N:'+nodeid)

    return "", "", ""

