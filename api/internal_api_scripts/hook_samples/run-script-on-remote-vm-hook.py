#! /usr/local/bin/python

import sys

from jobs.models import Job
from utilities.logger import get_thread_logger

"""Should be run at the post-provisioning hook point, after the VM is installed
and OS is running.

Requires that either the VM Template Password or Server Password parameter is
set on the server."""


def run(job, logger=None):
    # since this runs at post-provision time, it will be called regardless of
    # whether the job was a success or failure, but we only want to run this on
    # success
    if job.status != "SUCCESS":
        return "", "", ""

    # get the server and resource handler objects
    server = job.server_set.first()
    rh = server.resource_handler.cast()
    rh.init()

    creds = server.get_credentials()
    password = creds.get("password", None)
    username = creds.get("username", None)

    # the program to run must be passed separately from the arguments to that
    # program
    progpath = "/bin/echo"
    args = "'hello remote VM'"

    msg = "Running {} {} on server".format(progpath, args)
    job.set_progress(msg, logger=logger)

    output = rh.resource_technology.work_class.run_script_on_guest(
        server.resource_handler_svr_id,  # uuid
        username,
        password,
        args,
        progpath=progpath,
        return_stdout=True,
    )

    msg = "Output from script execution: {}".format(output)
    job.set_progress(msg, logger=logger)

    return "", "", ""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt job id>\n" % (sys.argv[0]))
        sys.exit(2)
    job_id = sys.argv[1]
    job = Job.objects.get(pk=job_id)
    logger = get_thread_logger(__name__)
    status, msg, err = run(job, logger)
