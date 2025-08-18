#!/usr/local/bin/python

import os
import pyVmomi
import requests
import sys

from jobs.models import Job
from utilities.helpers import get_ssl_verification
from utilities.logger import ThreadLogger
import resourcehandlers.vmware.pyvmomi_wrapper as pyvmomi

logger = ThreadLogger(__name__)

"""
Sample hook that copies a PowerShell script to a Windows server and runs it
"""

# Full path to the script to run on the guest
SCRIPT_MODULE = '/home/reina/cloudbolt/internal_api_scripts/hook_samples/SCCM-register.ps1'


def run(job, logger=None):
    logger = logger or ThreadLogger(__name__)
    servers = job.server_set.all()
    if not servers or job.status == 'FAILURE':
        return "", "", ""

    # make sure the script is executable now so when it is copied to each
    # server it is executable there as well
    os.chmod(SCRIPT_MODULE, 0755)

    failures = []
    for server in servers:
        logger.info('Preparng to run script on server {}'.format(server.hostname))
        cannot = cannot_run_script(server, logger=logger)
        if cannot:
            failures.append(cannot)
            continue

        failure, new_file_path = copy_file_to_guest(server, logger=logger)
        if failure:
            failures.append(failure)
            continue

        logger.info('Executing script on guest')
        try:
            output = server.execute_script(new_file_path)
            job.set_progress(
                'Script returned output: {}'.format(output))
        except RuntimeError:
            err = (
                'Failed to execute script on guest. Ensure that '
                'scripts can be executed on the server then try again.')
            failures.append(err)

    if failures:
        err = 'Failed to run scripts on server(s):\n{}'.format(
            '\n'.join(failures))
        return "FAILURE", "", err
    else:
        return "", "", ""


def cannot_run_script(server, logger=None):
    """
    Checks if the script can be run, if it cannot, return the reason, else
    return an empty string
    """
    rh = server.resource_handler.cast()
    creds = server.get_credentials()
    username = creds.get('username')
    passwd = creds.get('password')
    cannot = ''
    if not server.is_windows():
        cannot = 'Not yet supported for non-windows servers'
    elif not rh.can_run_scripts_on_servers:
        cannot = (
            "The server's Resource Handler does not support "
            "running scripts on servers.")
    elif server.power_status != 'POWERON':
        cannot = (
            'Cannot execute script because the server '
            'is not powered on'.format(server.hostname))
    elif not username:
        cannot = (
            'Username unknown for server {}. Be sure the "Server Username" '
            'parameter is set'.format(server.hostname)
        )
    elif not passwd:
        cannot = (
            'Password unknown for server {}. Be sure the "Server Password" '
            'or "VMware Template Password" parameter is set'.format(server.hostname)
        )
    if cannot and logger:
        logger.error(cannot)
    return cannot


def copy_file_to_guest(server, logger=None):
    """
    Use VMware's GuestOperationsManager to copy the script file to the guest

    Returns tuple: (error, file_location) where error is a string representing
    any errors and file_location is the location of the new file in the guest
    """
    creds = server.get_credentials()
    username = creds.get('username')
    passwd = creds.get('password')
    rh = server.resource_handler.cast()
    si = pyvmomi.get_connection(rh.ip, rh.port, rh.serviceaccount, rh.servicepasswd)
    vm = pyvmomi.get_vm_by_uuid(si, server.resource_handler_svr_id)
    fm = si.RetrieveContent().guestOperationsManager.fileManager
    auth = pyVmomi.vim.NamePasswordAuthentication(
        username=username, password=passwd, interactiveSession=False)
    file_size = os.path.getsize(SCRIPT_MODULE)
    gfa = pyVmomi.vim.GuestFileAttributes()
    guest_file_path = 'C:\\Users\\Administrator\\' + SCRIPT_MODULE.split('/')[-1]

    logger.info('Transfering script file to guest')
    put_url = fm.InitiateFileTransferToGuest(
        vm=vm,
        auth=auth,
        guestFilePath=guest_file_path,
        fileAttributes=gfa,
        fileSize=file_size,
        overwrite=True,
    )
    with open(SCRIPT_MODULE, 'rb') as f:
        response = requests.put(
            put_url, verify=get_ssl_verification(), data=f)
    if response.status_code != requests.codes.ok:
        return_text = '[{} Error] {}'.format(response.status_code, response.text)
        if logger:
            logger.error(return_text)
        return return_text, guest_file_path

    return None, guest_file_path


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print '  Usage:  {} <job_id>'.format(sys.argv[0])
        sys.exit(1)

    job = Job.objects.get(id=sys.argv[1])
    print run(job, logger=logger)
