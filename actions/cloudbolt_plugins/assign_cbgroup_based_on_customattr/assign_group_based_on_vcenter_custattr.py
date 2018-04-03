"""
Post-Sync RH
Map custom attributes/tags to Groups in CB
"""
import pyVmomi
from accounts.models import Group, GroupType
from common.methods import set_progress
from infrastructure.models import Server
from jobs.models import Job
from resourcehandlers.vmware import pyvmomi_wrapper
from resourcehandlers.vmware.pyvmomi_wrapper import get_connection

vm_custattr = '{{ vcenter_custom_attribute }}'

def run(job, logger=None, server=None, **kwargs):
    jp = job.job_parameters.cast()
    servers = Server.objects.filter(resource_handler__in=jp.resource_handlers.all())
    servers = servers.exclude(status="HISTORICAL")
    for server in servers:
        rh = server.resource_handler.cast()
        rh.get_api_wrapper()
        si = get_connection(rh.ip, rh.port, rh.serviceaccount, rh.servicepasswd, ssl_verification=False)
        vm = pyvmomi_wrapper.get_vm_by_name(si, server.get_vm_name())
        f = si.content.customFieldsManager.field
        for k, v in [(x.name, v.value) for x in f for v in vm.customValue if x.key == v.key]:
            if k == vm_custattr:
                try:
                    server.group = Group.objects.get(name=v)
                    server.save()
                except:
                    group_type, _ = GroupType.objects.get_or_create(group_type='Organization')
                    parent_group = None
                    group = Group.objects.create(name=v, type=group_type, parent=parent_group)
                    server.group = Group.objects.get(name=v)
                    server.save()
            else:
                group = Group.objects.get(name='Unassigned')
                server.group = group
                server.save()
    return "", "", ""
