"""
Useful for setting the primary IP for the server based on a DNS lookup on the
hostname.

To use this, make sure your network(s) have an IP pool associated with them so
the user is not asked to enter an IP.  The IP that C2 chooses from the pool
will be overwritten.
"""
# TODO: detach the RPVS from the server record so it does not consume a value
# from the pool

import logging
import socket


logger = logging.getLogger(__name__)


def run(job, logger=None):
    server = job.server_set.all()[0]
    hostname = server.hostname
    job.set_progress("Looking up IP address for '{}'".format(hostname))
    ip = socket.gethostbyname(hostname)
    job.set_progress("Setting NIC 1 IP in C2 to {}".format(ip))
    server.sc_nic_0_ip = ip
    server.save()
    return "", "", ""
