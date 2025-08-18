#! /usr/local/bin/python

import sys
import subprocess
import time
import shlex
import random

from jobs.models import Job
from utilities.logger import get_thread_logger
from utilities.exceptions import TimeoutException


def wait_for_ssh_connection(job, ip, logger=None):
    """
    Try to ssh to server with ip 'ip', wait up to 60s for available connection

    Raise TimeoutException if unable to connect
    """

    # cmd = "ssh administrator@{} 'ls'".format(ip)
    cmd = "ssh root@{} 'ls'".format(ip)
    args = shlex.split(cmd)
    start = time.time()

    while time.time() - start < 60:
        # run test command
        test_cmd = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        # test for successful connection
        time.sleep(random.randrange(2, 15))
        if test_cmd.poll() == 0:
            # subprocess completed sucessfully
            return
        else:
            msg = "Waiting up to 60s for available connection to DHCP server"
            if logger:
                logger.info(msg)
            try:  # kill process if hung
                test_cmd.terminate()
            except OSError:
                continue
    else:
        raise TimeoutException("Cannot connect to DHCP server")


def run(job, logger=None):
    """
    Given a job object, call to DHCP server to create an IP reservation

    Remote command requires the IP to reserve and the mac of the server.
    """

    # set variables
    dhcp_server_ip = "10.154.254.100"
    # scope = '10.120.0.0'

    # get ip of server
    srv = job.server_set.all()[0]
    ip = srv.ip

    if not ip:
        ip = getattr(srv, "sc_nic_0_ip", None)

    msg = "Reserving IP {} on DHCP server".format(ip)
    job.set_progress(msg, logger=logger)

    # get mac of server
    mac = srv.mac
    clean_mac = mac.replace(":", "")

    # only one ssh connection is allowed at once with PowerShell Server
    # before running the reservation command, confirm there is a connection
    # available
    try:
        wait_for_ssh_connection(job, dhcp_server_ip, logger=logger)
    except TimeoutException, e:
        return "FAILURE", "", e

    # send the command to the dhcp server

    # FOR Windows use:
    # remote_cmd = ("ssh Administrator@{dhcp_srv} "
    #             "'netsh dhcp server scope "
    #             "{scope} add reservedip {ip} "
    #             "{clean_mac}'".format(
    #                 dhcp_srv=dhcp_server_ip,
    #                 scope=scope,
    #                 ip=ip,
    #                 clean_mac=clean_mac,)
    #             )

    remote_cmd = (
        "ssh root@{dhcp_srv} "
        "'/etc/dhcp/add_entry {hostname}-{interface} {mac} {ip}'".format(
            dhcp_srv=dhcp_server_ip,
            hostname=srv.hostname,
            interface="0",
            mac=mac,
            ip=ip,
        )
    )

    remote_args = shlex.split(remote_cmd)

    if logger:
        msg = "running command '{}' on remote server".format("".join(remote_cmd))
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
                "Timeout reached when trying to " "create IP reservation on DHCP server"
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
    hook_status = ""
    if exit_status != 0:
        hook_status = "FAILURE"
        job.set_progress(stderr, logger=logger)
        stdout = "DHCP reservation failed with the following " "error:{}".format(stdout)
    else:
        progmsg = "DHCP reservation completed successfully"
        job.set_progress(progmsg, logger=logger)

    return hook_status, stdout, stderr


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt job id>\n" % (sys.argv[0]))
        sys.exit(2)
    job_id = sys.argv[1]
    job = Job.objects.get(pk=job_id)
    logger = get_thread_logger(__name__)
    status, msg, err = run(job, logger)
