"""
A hook that will replace the server ip from 'dhcp' with the infoblox reserved
IP value when applicable
"""

import traceback
import sys


def run(job, logger=None):
    debug("Running hook {}. job.id={}".format(__name__, job.id), logger)
    try:
        for server in job.server_set.all():
            if server.ip == 'dhcp' and job.children_jobs.all():
                #TODO: make sure the first sub job is the IP allocation job
                alloc_job = job.children_jobs.all()[0]
                ip = str(alloc_job.output).split("'")[19]

                msg = ("Updating server IP from 'dhcp' to '{}'").format(ip)
                job.set_progress(msg, logger=logger)
                server.ip = ip
                server.save()
    except:
        outmsg = "Aborting job because of a dhcp replacement hook error"
        tb = traceback.format_exception(*sys.exc_info())
        errmsg = "\n" + "\n".join(tb)
        return ("FAILURE", outmsg, errmsg)
    return "", "", ""


def debug(message, logger):
    if logger:
        logger.debug(message)
    else:
        print message
