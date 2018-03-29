import requests
from orionsdk import SwisClient
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from utilities.models import ConnectionInfo

def run(job=None, *args, **kwargs):
    # Disable SSL errors
    verify = False
    if not verify:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Get SolarWinds ConnectionInfo
    solarwinds = ConnectionInfo.objects.get(name='SolarWinds')
    swis = SwisClient(solarwinds.ip, solarwinds.username, solarwinds.password)
    if not solarwinds:
        return "FAILURE", "", "Missing required SolarWinds connection info. (Admin -> Connection Info -> New Connection Info)"

    # Get Server Info
    server = job.server_set.first()
    ip_address = server.ip

    # Find the Uri you want to delete based on a SWQL query
    results = swis.query("select ipaddress, caption, uri from orion.nodes where ipaddress = '{}'".format(ip_address))

    # Use as needed
    if len(results['results']) > 1:
        print('Refine your search. Found more than one node matching that criteria.')
    elif len(results['results']) == 1:
        print("Deleting {}".format(results['results'][0]['ipaddress']))
        response = swis.delete(results['results'][0]['uri'])
        print("Done")
    else:
        print("Nothing to delete from SolarWinds")

    return "","",""
