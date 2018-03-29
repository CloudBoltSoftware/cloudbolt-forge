"""
SolarWinds IPAM
Add Node and Pollers
IV. Pre-Create Resource
"""
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
    # Get Node Info
    server = job.server_set.first()
    hostname = "{}.{}".format(server.hostname, server.env_domain)

    # Get/set next available IP
    subnet_name = '{{ sw_ipnet }}'
    next_ip = swis.query("SELECT TOP 1 I.Status, I.DisplayName FROM IPAM.IPNode I WHERE Status=2 AND I.Subnet.DisplayName = '{}'".format(subnet_name))
    server.ip = next_ip.values()[0][0].values()[1]
    server.save()

    # Setup Node Properties
    props = {
        'IPAddress': server.ip,
        'EngineID': 1,
        'ObjectSubType': 'Agent',
        'Caption': hostname,
        'DNS': hostname,
        'Description': 'Added by CloudBolt',
        'Contact': server.owner,
        }

    #Create the Node
    job.set_progress("Adding '{}' to SolarWinds".format(hostname))
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

    return "","",""
