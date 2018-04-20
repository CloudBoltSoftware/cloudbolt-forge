"""
SolarWinds IPAM
Validate Unique IP & Hostname
Trigger Point III.
"""
if __name__ == '__main__':
    import os
    import sys
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.append('/opt/cloudbolt')
    django.setup()

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

    # Query Solarwinds for the FQDN & IP
    job.set_progress("Checking if node '{}' is already in SolarWinds".format(server.hostname))
    hostname_results = swis.query("select n.ipaddress, n.nodename from orion.nodes n where nodename = '{}'".format(server.hostname))

    if len(next(iter(hostname_results.values()))) == 0:
        set_progress("'{}' not found in Solarwinds.".format(server.hostname))
    else:
        return 'FAILURE', '', "Found node '{}' in Solarwinds.".format(server.hostname)

    return "", "", ""

if __name__ == '__main__':
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    run = run(job)
    if run[0] == 'FAILURE':
        set_progress(run[1])