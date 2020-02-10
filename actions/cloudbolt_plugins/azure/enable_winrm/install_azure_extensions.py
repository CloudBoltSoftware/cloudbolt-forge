import json
import time
from common.methods import set_progress
from servicecatalog.models import ProvisionServerServiceItem

def run(job=None, logger=None, service=None, server=None, **kwargs):
    """
    Install an extension on the specified server or server tier.
    Can be used as a server action, a service action, or a blueprint action.
    """
    # Change the following section when developing an action for a new extension.

    EXTENSION_NAME = "{{ extension_name }}"
    PUBLISHER = "{{ publisher }}"
    VERSION = "{{ version }}"
    settings = """{{ settings }}"""
    protected_settings = """{{ protected_settings }}"""


    set_progress("Adding {} extension to {}".format(EXTENSION_NAME, server))
    resource_handler = server.resource_handler.cast()
    if PUBLISHER == "":
        PUBLISHER = "Microsoft.Compute"
    if protected_settings == "":
        protected_settings = "{}"

    server_info = resource_handler.tech_specific_server_details(server)
    server_name = server.hostname
    resource_group_name = server_info.resource_group
    location = server_info.location

    w = resource_handler.get_api_wrapper()

    from azure.mgmt.compute.models import VirtualMachineExtension

    extension_parameters = VirtualMachineExtension(
        location=location,
        publisher=PUBLISHER,
        virtual_machine_extension_type=EXTENSION_NAME,
        type_handler_version=VERSION,
        settings=json.loads(settings),
        protected_settings=json.loads(protected_settings)
    )
    poller = w.compute_client.virtual_machine_extensions.create_or_update(
        resource_group_name,
        server_name,
        EXTENSION_NAME,
        extension_parameters
    )
    poller.wait(timeout=240)

    has_failures = False
    status = "FAILURE" if has_failures else "SUCCESS"

    return status, "", ""