#!/usr/local/bin/python

"""
Sample hook for converting a VM to a template.

This could be used as a server action or an action in a service blueprint.

Warning: this will power off live VMs and convert them to templates! Use with care.
"""
from resourcehandlers.vmware import pyvmomi_wrapper


def run(job, logger=None):
    server = job.server_set.all()[0]

    # get an pyvmomi session instance object so we can make calls into the vCenter API
    # for more info:
    # http://vmware.github.io/pyvmomi-community-samples/#getting-started
    # http://pubs.vmware.com/vsphere-55/index.jsp?topic=%2Fcom.vmware.wssdk.apiref.doc%2Fvim.VirtualMachine.html
    rh = server.resource_handler.cast()
    rh.init()
    pyvmomi = rh.resource_technology.work_class._get_connection()

    # use CB's pyvmomi_wrapper for an easy way to get the VM object from the UUID
    vm = pyvmomi_wrapper.get_vm_by_uuid(pyvmomi, server.resource_handler_svr_id)

    # power it off and change it to a template
    server.power_off()
    vm.MarkAsTemplate()

    return "", "", ""


if __name__ == "__main__":
    import sys
    from jobs.models import Job

    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    job.status = "SUCCESS"
    job.save()
    print(run(job))
