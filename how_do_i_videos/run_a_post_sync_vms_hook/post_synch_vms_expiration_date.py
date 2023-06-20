from datetime import datetime
from infrastructure.models import Server
from resourcehandlers.vmware.models import VsphereResourceHandler
from pyVmomi import vim
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

"""
Hook used at the post syncvms hook point to set expiration date on newly synced
servers.

Finds all servers that do not yet have the expiration_date custom field set,
then checks vCenter to see if the server has an attribute with a lease date. 
If there is a lease date in that attribute, this will then set the 
expiration_date custom field on the server to the lease date set in the 
attribute.

Make sure that the action has a default value set for Days Before Expire.

Remove the hour, minute, second, and microsecond from the datetime object
because our current datepicker widget does not handle these values.
"""

# Expecting the name of the attribute in vCenter that represents the lease date
LEASE_DATE_ATTRIBUTE = "{{lease_date_attribute}}"

def run(job, logger=None, **kwargs):
    # Get all VC RHs - this allows us to loop through the servers for each RH
    # and reuse the same pyvmomi wrapper object
    vcs = VsphereResourceHandler.objects.all()

    for vc in vcs:
        # Get all servers without a current expiration date for vCenter RHs
        servers = Server.objects.filter(
            status="ACTIVE",
            resource_handler__id=vc.id,
        ).exclude(custom_field_values__field__name="expiration_date")
        # Get the pyvmomi wrapper
        pyvmomi_wrapper = vc.get_api_wrapper()
        # Get the pyvmomi server object
        si = pyvmomi_wrapper._get_connection()
        search_index = si.content.searchIndex
        try:
            attribute_key = get_attribute_key(si, LEASE_DATE_ATTRIBUTE, vc)
        except Exception as e:
            logger.debug(f"Attribute {LEASE_DATE_ATTRIBUTE} not found in "
                         f"vCenter: {vc.ip}. Skipping")
            continue
        job.set_progress(f'Starting query for servers in vCenter {vc.ip}')
        for server in servers:
            try:
                vc_vm = get_vc_vm_from_server(server, search_index)
            except Exception as e:
                logger.debug(f"Could not find server {server.hostname} in "
                             f"vCenter. Skipping")
                continue
            try:
                lease_date = get_attribute_value(vc_vm, attribute_key)
            except Exception as e:
                if server.hostname == "mb-se-demo-003":
                    logger.debug(f'Error: {e}')
                logger.debug(f"No lease date attribute value found for server "
                             f"{server.hostname} in vCenter. Skipping")
                continue
            try:
                expire = datetime.strptime(lease_date, "%m/%d/%Y")
            except ValueError:
                logger.debug("Lease date is not in the format %m/%d/%Y, trying"
                             " two digit year")
                try:
                    expire = datetime.strptime(lease_date, "%m/%d/%y")
                except ValueError:
                    logger.debug("Lease date is not in the format %m/%d/%y, "
                                 "skipping")
                    continue
            job.set_progress(f"Setting expiration date to {expire} for server"
                             f" {server.hostname}")
            server.expiration_date = expire
            server.save()

    return "", "", ""

def get_vc_vm_from_server(server, search_index):
    # Using the search_index get the Virtual Machine from pyvmomi matching the
    # server instance uuid
    vm = search_index.FindByUuid(None, server.vmwareserverinfo.instance_uuid,
                                 True, True)
    if not vm:
        raise Exception(f"VM not found in vCenter for server {server.hostname}")
    return vm


def get_attribute_key(si, attribute_name, rh):
    """
    Get the attribute key from the VM object
    :param vm: pyvmomi Virtual Machine object
    :param attribute_name: name of the attribute to get the key for
    :return: key of the attribute
    """
    content = si.RetrieveContent()
    cfm = content.customFieldsManager
    for field in cfm.field:
        if field.name == attribute_name:
            return field.key

    raise Exception(f"Attribute {attribute_name} not found in vCenter: {rh.ip}")


def get_attribute_value(vm, attribute_key):
    """
    Get the attribute value from the VM object
    :param vm: pyvmomi Virtual Machine object
    :param attribute_key: numerical key of the attribute to get the value for
    :return: value of the attribute
    """
    # Get the lease date attribute from the VM
    for value in vm.customValue:
        if value.key == attribute_key:
            return value.value
    raise Exception(f"Attribute Value {attribute_key} not found on VM "
                    f"{vm.name}")
