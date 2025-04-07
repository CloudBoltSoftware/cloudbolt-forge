"""
For each successful job, if a custom field 'create_qpc_hypervisor' is set,
create a new handler and environment for a group.
"""
import logging
import traceback
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from c2_wrapper import create_qemu_resource_handler, create_nvp_qemu_link
from resourcehandlers.models import ResourceTechnology
from networks.nicira.models import NVPControllerHandler

logger = logging.getLogger(__name__)


def run(job, logger=None):
    if job.status != "SUCCESS":
        return "", "", ""

    params = job.job_parameters.cast()
    try:
        create_qpc = params.custom_field_values.get(field__name="create_qpc_hyper")
    except ObjectDoesNotExist:
        return "", "", ""

    if create_qpc.value == True:
        server = job.server_set.all()[0]
        job.set_progress(
            "Registering new server as a Qemu/KVM hypervisor...", logger=logger
        )

        # TODO (Mike Albert)

        # Sets up host specific settings for QPC (network/hostname information)
        # based upon values provided
        # - sh /root/templates/qpc/deployQPC.sh
        # * I think this may not be needed if we are doing net config thru CB

        # Configures bridges and which OVS manager to point to for management
        # based upon values provided
        # - sh /root/templates/qpc/deployOVS.sh
        # ENTER CODE HERE

        # Creating the qpc hypervisor on the fly
        qemu_rt = ResourceTechnology.objects.filter(modulename__contains=".qemu.")
        if not qemu_rt:
            return ("FAILURE", "Oops!", "Cannot create a Qemu/KVM resource handler.")
        qemu_rt = qemu_rt[0]
        name = "Auto Generate QPC - %s" % server.hostname
        try:
            rh_pw = server.initial_password
        except AttributeError as e:
            # default to 'cloudbolt' in test env, should fail the job in prod?
            rh_pw = "cloudbolt"
        rh = create_qemu_resource_handler(
            name, server.ip, "22", "ssh", "root", rh_pw, qemu_rt
        )
        nvp = NVPControllerHandler.objects.all()
        if not nvp:
            # nothing to do here
            return "", "", ""
        nvp = nvp[0]
        create_nvp_qemu_link(nvp, rh, {"qemu_network": " br-int"})

        # TODO (Auggy)
        # Create new environment using new rh and associate it with a customer

    return "", "", ""
