#!/usr/bin/env python

"""
Used to configure some prerequisites that a CenturyLink VM needs before we can
successfully run remote scripts on it. Namely, captures its credentials and
stores them on the CB server object and adds a public IP address so it's
accessible.

Meant to be run as an orchestration action during prov on CTL servers only. Must
be run before any remote script. Enables a CIT test for remote scripts on CTL.
"""

if __name__ == '__main__':
    import django
    django.setup()

import requests
from common.methods import set_progress


def run(job, logger=None, **kwargs):
    # Get server (there's only ever one per prov job)
    server = job.server_set.first()

    if not server:
        return "FAILURE", "", "No server to prep!"

    rh = server.resource_handler
    rh = rh.cast()
    wrapper = rh.get_api_wrapper()

    # 1st prereq is getting and storing username & password
    set_progress("Pulling credentials from CTL for server {}".format(server.hostname))
    url = "{}servers/{}/{}/credentials".format(wrapper.BASE_URL,
                                               wrapper.account_alias,
                                               server.ctlserverinfo.ctl_server_id)
    response = requests.get(url, headers=wrapper.headers,
                            proxies=wrapper.proxies, verify=False)
    creds = response.json()
    server.username = creds.get('userName')
    server.password = creds.get('password')

    # 2nd prereq is adding a public IP in CTL
    set_progress("Adding public IP to server {} associated with private "
                 "IP {}. This may take a while.".format(
                     server.hostname, server.ip))
    url = "servers/{}/{}/publicIPAddresses".format(wrapper.account_alias,
                                                     server.ctlserverinfo.ctl_server_id)
    payload = {
        "internalIPAddress": server.ip,
        "ports": [
            {
                "protocol": "TCP",
                "port": "22"
            }
        ]
    }
    response = wrapper.request_and_wait(url, method='post', json=payload)
    server.refresh_info()
    return "SUCCESS", "", ""


if __name__ == '__main__':
    from utilities.logger import ThreadLogger
    logger = ThreadLogger(__name__)
    print run(None, logger)
