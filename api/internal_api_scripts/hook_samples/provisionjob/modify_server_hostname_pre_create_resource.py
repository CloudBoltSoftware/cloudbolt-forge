import traceback
import sys


def run(job, logger=None):
    debug("in %s job.id=%s" % (__name__, job.id), logger)

    # hook to add a prefix to the hostname of any server whose group
    # has an agency ID parameter associated with it
    try:
        server = job.server_set.all()[0]
        agency_id = getattr(server, "agency_id", None)
        if not agency_id:
            prog_msg = "Not altering the hostname as no agency_id was found."
            job.set_progress(prog_msg, logger=logger)
            return "", "", ""

        old_hostname = server.hostname
        server.hostname = "e%s%s" % (agency_id, server.hostname)
        server.save()
        prog_msg = "Prefixed hostname with agency ID.  %s -> %s" \
            % (old_hostname, server.hostname)
        job.set_progress(prog_msg, logger=logger)
    except:
        outmsg = "Aborting job based on pre resource hook error"
        tb = traceback.format_exception(*sys.exc_info())
        errmsg = "\n" + "\n".join(tb)
        return ("FAILURE", outmsg, errmsg)

    return "", "", ""


def debug(message, logger):
    if logger:
        logger.debug(message)
    else:
        print message
