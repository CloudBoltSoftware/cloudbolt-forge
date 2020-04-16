#! /usr/local/bin/python

import sys
import subprocess
import time
import shlex

from jobs.models import Job
from utilities.logger import get_thread_logger

"""Post-Decommission Hook"""


def delete_reservation(job, srv, logger=None):
    """
    Given a server object and job object, call to DHCP server to remove IP
    reservation

    Returns status, stdout, stderr
    """

    # set variables
    dhcp_server_ip = "10.60.72.123"
    scope = "10.60.72.0"

    # get ip and mac of server
    ip = srv.ip
    mac = srv.mac
    clean_mac = mac.replace(":", "")

    msg = "Now working on server '{}'".format(srv.hostname)
    job.set_progress(msg, logger=logger)

    # send the command to the dhcp server
    remote_cmd = (
        "ssh Administrator@{dhcp_srv} "
        "'netsh dhcp server scope "
        "{scope} delete reservedip {ip} "
        "{clean_mac}'".format(
            dhcp_srv=dhcp_server_ip, scope=scope, ip=ip, clean_mac=clean_mac,
        )
    )

    remote_args = shlex.split(remote_cmd)

    if logger:
        msg = "running command '{}' on remote server".format(remote_cmd)
        logger.debug(msg)

    netsh_cmd = subprocess.Popen(
        remote_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # wait for process to complete
    timeout = 15
    while not netsh_cmd.poll():
        if netsh_cmd.poll() == 0:
            break
        if timeout:
            timeout -= 1
            time.sleep(1)
        else:
            stderr = (
                "Timeout reached when trying to "
                "remove IP reservation from DHCP server"
            )
            job.set_progress(stderr, logger=logger)
            netsh_cmd.terminate()
            return "FAILURE", "", stderr

    # get and process stderr, stdout, and returncode
    stdout = "".join(netsh_cmd.stdout.readlines())
    stdout = stdout.replace("\r\n", " ")
    stderr = "".join(netsh_cmd.stderr.readlines())
    stderr = stderr.replace("\r\n", " ")
    exit_status = netsh_cmd.returncode

    if logger:
        logger.info("Reservation exit status: {}".format(exit_status))
        logger.info("Reservation stdout: {}".format(stdout))
        logger.info("Reservation stderr: {}".format(stderr))

    # return success or failure
    deletion_status = ""
    if exit_status != 0:
        deletion_status = "FAILURE"
        stdout = (
            "DHCP reservation removal failed with the following "
            "error:{}".format(stdout)
        )
        job.set_progress(stderr, logger=logger)
    else:
        progmsg = "Reservation removed"
        job.set_progress(progmsg, logger=logger)

    return deletion_status, stdout, stderr


def run(job, logger=None):
    msg = "Removing IP reservations from DHCP server"
    job.set_progress(msg, logger=logger)

    hook_status = ""
    hook_stdout = ""
    hook_stderr = ""
    for srv in job.server_set.all():
        status, stdout, stderr = delete_reservation(job, srv, logger=logger)
        if status:
            hook_status = "FAILURE"
            hook_stdout = (
                "Removal of IP reservations from DHCP server completed with error(s)"
            )

    progmsg = "Removal of DHCP reservations complete"
    job.set_progress(progmsg, logger=logger)

    return hook_status, hook_stdout, hook_stderr


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt job id>\n" % (sys.argv[0]))
        sys.exit(2)
    job_id = sys.argv[1]
    job = Job.objects.get(pk=job_id)
    logger = get_thread_logger(__name__)
    status, msg, err = run(job, logger)
