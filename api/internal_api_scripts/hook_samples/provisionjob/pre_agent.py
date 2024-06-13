import sys
import time


def run(job, logger=None):
    svr = job.server_set.all()[0]
    facil = svr.facility_name
    print "in %s job.id=%s" % (__name__, job.id)
    time.sleep(60)
    return "", "", ""
