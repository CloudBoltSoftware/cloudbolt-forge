"""
SolarWinds IPAM
Validate Unique IP & Hostname
Provision Server - Trigger Point III.
"""
import orionsdk
import requests
from common.methods import set_progress
from jobs.models import Job
from utilities.models import ConnectionInfo
from orionsdk import SwisClient

def run(job=None, *args, **kwargs):
    # Disable SSL errors
    verify = False
    if not verify:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning 
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Get SolarWinds ConnectionInfo
    solarwinds = ConnectionInfo.objects.get(name='SolarWinds')
    swis = SwisClient(solarwinds.ip, solarwinds.username, solarwinds.password)
    if not solarwinds:
        return "FAILURE", "", "Missing required SolarWinds connection info. (Admin -> Connection Info -> New Connection Info)"

    # Get Server Info
    server = job.server_set.first()
    hostname = "{}.{}".format(server.hostname, server.env_domain)
    #ip_address = server.ip

    # Query Solarwinds for the FQDN & IP
    job.set_progress("Checking if hostname '{}' is already in SolarWinds".format(hostname))
    hostname_results = swis.query("select n.ipaddress, n.nodename from orion.nodes n where nodename = '{}'".format(hostname))
    #ip_results = swis.query("select n.ipaddress, status from orion.nodes n where status=2 and ipaddress ='{}'".format(ip_address))

    #if len(hostname_results) | len(ip_results) > 0:
    if len(hostname_results.values()[0]) > 0:
        return 'FAILURE', '', "Found hostname '{}' in Solarwinds.".format(hostname)
    else:
        job.set_progress("'{}' not found in Solarwinds.".format(hostname))
    return "","",""
