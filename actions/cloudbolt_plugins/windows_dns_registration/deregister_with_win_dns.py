import sys

import pyVmomi

from jobs.models import Job
from resourcehandlers.vmware import pyvmomi_wrapper
from resourcehandlers.vmware.pyvmomi_wrapper import run_script_on_guest, get_connection
from utilities.models import ConnectionInfo

DNS_ZONE = "cloudbolt.loc"
DNS_CONNECTION_INFO = "WindowsDnsServer"
VMW_CONNECTION_INFO = "vCenterServer"


def run(job, logger=None):
    dns = ConnectionInfo.objects.get(name=DNS_CONNECTION_INFO)
    vmw = ConnectionInfo.objects.get(name=VMW_CONNECTION_INFO)
    si = get_connection(vmw.ip, vmw.port, vmw.username, vmw.password)

    for server in job.server_set.all():
        del_host = server.hostname
        del_ip = server.ip
        vm = pyvmomi_wrapper.get_object_by_name(si, pyVmomi.vim.VirtualMachine, dns.ip)

        # Here's the script that is being run on the remote VM
        script = "dnscmd /recorddelete {} {} a /f".format(DNS_ZONE, del_host)

        job.set_progress("Registering DNS record for {} at {}.".format(del_host, del_ip))
        run_script_on_guest(si, vm, dns.username, dns.password, script, is_windows=True)

    return "", "", ""


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <Job ID>\n" % sys.argv[0])
        sys.exit(2)

    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    run(job)
