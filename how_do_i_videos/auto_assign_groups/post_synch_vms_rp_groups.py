"""
A Post Sync VMs Hook for the VMware Resource Handler. This hook will
find all CloudBolt VMware servers in the unassigned group, and then:
1. Check vCenter to see if the VM belongs to a Resource Pool.
2. If it does, then we will take any portion of the resource pool name before
the first "-" and look for a group that corresponds to that string
(case-insensitive)
3. If the group exists, then we will assign the server to that group. If not,
log a warning and continue.

Prerequisites:
- Resource pool names should match the standard of "my group-anyotherstringhere"
- The group needs to already exist in CloudBolt
"""
from accounts.models import Group
from common.methods import set_progress
from infrastructure.models import Server
from resourcehandlers.vmware.models import VsphereResourceHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, logger=None, **kwargs):
    set_progress("Starting check of VMware VMs to sync group from resource "
                 "pool")
    vcs = VsphereResourceHandler.objects.all()

    for vc in vcs:
        servers = Server.objects.filter(
            status="ACTIVE",
            resource_handler__id=vc.id,
            group__name="Unassigned",
        )
        # Get the pyvmomi wrapper
        pyvmomi_wrapper = vc.get_api_wrapper()
        # Get the pyvmomi server object
        si = pyvmomi_wrapper._get_connection()
        search_index = si.content.searchIndex

        for server in servers:
            logger.info(f"Checking group for server {server.hostname}")
            try:
                vc_vm = get_vc_vm_from_server(server, search_index)
            except Exception as e:
                logger.debug(f"Could not find server {server.hostname} in "
                             f"vCenter. Skipping")
                continue
            try:
                resource_pool = vc_vm.resourcePool.name
            except Exception as e:
                logger.debug(f"Could not find resource pool for server "
                             f"{server.hostname} in vCenter. Skipping")
                continue
            try:
                group_name = resource_pool.split("-")[0]
            except Exception as e:
                logger.debug(f"Could not find group name for server "
                             f"{server.hostname} in vCenter. Skipping")
                continue
            try:
                group = Group.objects.get(name__iexact=group_name)
            except Group.DoesNotExist:
                logger.debug(f"Could not find group {group_name} in CloudBolt. "
                             f"Skipping")
                continue
            except Group.MultipleObjectsReturned:
                logger.warning(f"Multiple groups found with name {group_name}. "
                               f"Skipping")
                continue

            server.group = group
            server.save()
            set_progress(f"Set group for server {server.hostname} to "
                         f"{group.name}")
    return "", "", ""


def get_vc_vm_from_server(server, search_index):
    # Using the search_index get the Virtual Machine from pyvmomi matching the
    # server instance uuid
    vm = search_index.FindByUuid(None, server.vmwareserverinfo.instance_uuid,
                                 True, True)
    if not vm:
        raise Exception(f"VM not found in vCenter for server {server.hostname}")
    return vm
