"""
CloudBolt Plugin with local execution
Run as a Post-Provison orchestration action
"""
if __name__ == '__main__':
    import os
    import sys
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.append('/opt/cloudbolt')
    django.setup()

from common.methods import set_progress
from jobs.models import Job
from resourcehandlers.vmware import pyvmomi_wrapper
from resourcehandlers.vmware.pyvmomi_wrapper import get_connection
from pyVim.task import WaitForTask
from pyVmomi import vim
from time import sleep

def run(job=None, **kwargs):
    server = job.server_set.first()
    if server.cores_per_socket:
        rh = server.resource_handler.cast()
        rh.get_api_wrapper()
        si = get_connection(rh.ip, rh.port, rh.serviceaccount, rh.servicepasswd, ssl_verification=False)
        vm = pyvmomi_wrapper.get_vm_by_name(si, server.get_vm_name())
        if server.power_status != 'POWEROFF':
            set_progress('Powering down server {} for Cores per socket reconfiguration.'.format(server))
            server.power_off()
            sleep(10)
        cspec = vim.vm.ConfigSpec()
        cspec.numCoresPerSocket = server.cores_per_socket
        WaitForTask(vm.Reconfigure(cspec))
        server.power_on()
    else:
        pass
    return "", "", ""

if __name__ == '__main__':
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    run = run(job)
    if run[0] == 'FAILURE':
        set_progress(run[1])
