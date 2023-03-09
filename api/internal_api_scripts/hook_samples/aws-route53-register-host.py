from boto.route53.connection import Route53Connection
import traceback
import sys

AWS_ACCESS_KEY_ID = "<INSERT VALUE HERE>"
AWS_SECRET_ACCESS_KEY = "<INSERT VALUE HERE>"
ZONE = "<INSERT ZONE HERE>"  # include trailing period
IP_ADDR = "<INSERT IP HERE>"
TTL = 3600


def register_a_rec(hostname):
    conn = Route53Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    zone = conn.get_zone(ZONE)
    zone.add_a(hostname, IP_ADDR, ttl=TTL)


def run(job, logger, **kwargs):

    if job.status == "FAILURE":
        return "", "", ""

    outmsg = "Problem during DNS registration with AWS Route 53."
    should_warn = False

    for server in job.server_set.all():
        fqdn = "{}.{}".format(server.hostname, ZONE)
        job.set_progress("Creating DNS A record: {}".format(fqdn))
        try:
            register_a_rec(fqdn)
        except:
            outmsg += '\nError registering: "{}"'.format(fqdn)
            outmsg += "\n\tCheck AWS creds and zone name ({})".format(ZONE)
            tb = traceback.format_exception(*sys.exc_info())
            errmsg += "\n" + "\n".join(tb)
            should_warn = True

    if should_warn:
        return ("WARNING", outmsg, errmsg)

    return "", "", ""
