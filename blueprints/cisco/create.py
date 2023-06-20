'''
ORDER Workflow
Select organisation
Choose if to create a service profile from another service profile template.
Select the service profile template.
Provide a name for the service profile you want to create.
Choose type of server being associated with the service profile i.e Blade or Rack servers
Provide a mac pool name to be used to provide mac address for the servers.

'''
import json
import time
import requests
import xmltodict

from ucscsdk.ucschandle import UcscHandle
from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.ucseventhandler import UcsEventHandle

from ucsmsdk.mometa.ls.LsServer import LsServer
from ucsmsdk.mometa.lsboot.LsbootDef import LsbootDef
from ucsmsdk.mometa.lsboot.LsbootStorage import LsbootStorage
from ucsmsdk.mometa.lsboot.LsbootLocalStorage import LsbootLocalStorage
from ucsmsdk.mometa.lsboot.LsbootDefaultLocalImage import LsbootDefaultLocalImage
from ucsmsdk.mometa.vnic.VnicEther import VnicEther
from ucsmsdk.mometa.vnic.VnicEtherIf import VnicEtherIf
from ucsmsdk.mometa.vnic.VnicFcNode import VnicFcNode

from ucsmsdk import ucsmethodfactory as mf
from ucsmsdk.mometa.ls.LsServer import LsServerConsts
from ucscsdk import ucscbasetype
from ucscsdk.ucscbasetype import DnSet, Dn
from ucscsdk.mometa.ls.LsBinding import LsBinding

from utilities.mail import email
from common.methods import set_progress
from utilities.models import ConnectionInfo
from ipam.infoblox.models import InfobloxIPAM
from infrastructure.models import CustomField
from utilities.helpers import get_ssl_verification

conn, _ = ConnectionInfo.objects.get_or_create(name='Cisco UCS')

try:
    handler = UcscHandle(conn.ip, conn.username, conn.password, conn.port)
except Exception:
    # not a UCS central server. Connect using UcsHandle
    handler = UcsHandle(conn.ip, conn.username, conn.password, conn.port)


def generate_options_for_organization(**kwargs):
    if not handler.cookie:
        handler.login()
    options = ['org-root']
    organizations = handler.query_children(in_dn="org-root", class_id="OrgOrg")
    options.extend([organization.dn for organization in organizations])
    handler.logout()
    return options


def generate_options_for_service_profile_template(control_value=None, **kwargs):
    if control_value:
        if not handler.cookie:
            handler.login()
        # Get all service profile in an organization(control_value)
        service_profile_templates = handler.query_children(in_dn=control_value, class_id="lsServer")
        handler.logout()
        return [sp.dn for sp in service_profile_templates]
    return []


def generate_options_for_chassis(**kwargs):
    if not handler.cookie:
        handler.login()
    # Get all chassis
    chassis = handler.query_children(in_dn=f"sys", class_id="equipmentChassis")
    handler.logout()
    return [chass.dn for chass in chassis]


def generate_options_for_ucs_server_dn(control_value=None, **kwargs):
    if control_value:   
        if not handler.cookie:
            handler.login()
        # Get all blades
        blades = handler.query_children(in_dn=control_value, class_id="computeBlade")
        handler.logout()
        return [blade.dn for blade in blades]
    return []


def generate_options_for_rack_server(**kwargs):
    if not handler.cookie:
        handler.login()
    servers = handler.query_children(in_dn=f"sys", class_id="ComputeRackUnit")
    handler.logout()
    return [server.dn for server in servers]


def run(job, resource, *args, **kwargs):
    username = conn.username
    password = conn.password

    organization = "{{ organization }}"
    service_profile_template = "{{ service_profile_template }}"
    create_sp_from_sp_template = "{{ create_sp_from_sp_template }}"
    service_profile_name = "{{ service_profile_name }}"
    service_profile_description = "{{ service_profile_description }}"
    use_blade_servers = "{{ use_blade_servers }}"
    chassis = "{{ chassis }}"
    ucs_server_dn = "{{ ucs_server_dn }}"
    ucs_rack_server = "{{ rack_server }}"
    mac_pool_name = "{{ mac_pool_name }}"

    service_profile_server_dn, _ = CustomField.objects.get_or_create(name="service_profile_server_dn", label="Service Profile Server DN", type="STR", show_on_servers=True)

    handler.login()
    ucs_event_handler = UcsEventHandle(handler)

    # create SP in an org
    set_progress(f"Creating service profile named {service_profile_name}")
    if create_sp_from_sp_template == "True":
        dn_set = ucscbasetype.DnSet()
        dn_set.child_add(Dn(value=f"{service_profile_name}"))

        xml_element = mf.ls_instantiate_n_named_template(
            cookie=handler.cookie,
            dn=service_profile_template,
            in_error_on_existing="true",
            in_name_set=dn_set,
            in_target_org=organization
        )
        handler.process_xml_elem(xml_element)
    else:
        mo = LsServer(
            parent_mo_or_dn=organization, vmedia_policy_name="",
            ext_ip_state="none", bios_profile_name="",
            mgmt_fw_policy_name="", agent_policy_name="",
            mgmt_access_policy_name="", dynamic_con_policy_name="",
            kvm_mgmt_policy_name="", sol_policy_name="", uuid="0",
            descr=service_profile_description, stats_policy_name="default", policy_owner="local",
            ext_ip_pool_name="ext-mgmt", boot_policy_name="", usr_lbl="",
            host_fw_policy_name="", vcon_profile_name="",
            ident_pool_name="", src_templ_name="",
            local_disk_policy_name="", scrub_policy_name="",
            power_policy_name="default", maint_policy_name="",
            name=service_profile_name, resolve_remote="yes"
        )
        mo_1 = LsbootDef(
            parent_mo_or_dn=mo, descr="", reboot_on_update="no",
            adv_boot_order_applicable="no", policy_owner="local",
            enforce_vnic_name="yes", boot_mode="legacy"
        )
        mo_1_1 = LsbootStorage(parent_mo_or_dn=mo_1, order="1")
        mo_1_1_1 = LsbootLocalStorage(parent_mo_or_dn=mo_1_1, )
        mo_1_1_1_1 = LsbootDefaultLocalImage(parent_mo_or_dn=mo_1_1_1, order="1")
        mo_2 = VnicEther(
            parent_mo_or_dn=mo, nw_ctrl_policy_name="", name="eth0",
            admin_host_port="ANY", admin_vcon="any",
            stats_policy_name="default", admin_cdn_name="",
            switch_id="A", pin_to_group_name="", mtu="1500",
            qos_policy_name="", adaptor_profile_name="",
            ident_pool_name=mac_pool_name, order="unspecified", nw_templ_name="",
            addr="derived"
        )
        mo_2_1 = VnicEtherIf(
            parent_mo_or_dn=mo_2, default_net="yes",
            name="default"
        )
        mo_3 = VnicFcNode(
            parent_mo_or_dn=mo, ident_pool_name="",
            addr="pool-derived"
        )
        handler.add_mo(mo)

    # Associate a server to a service profile.
    if use_blade_servers == "True":
        set_progress(f"Associating service profile {service_profile_name} with {ucs_server_dn}")
        mo = LsBinding(
            parent_mo_or_dn=f"{organization}/ls-{service_profile_name}",
            pn_dn=ucs_server_dn, restrict_migration="no"
        )
    else:
        set_progress(f"Associating service profile {service_profile_name} with {ucs_rack_server}")
        mo = LsBinding(
            parent_mo_or_dn=f"{organization}/ls-{service_profile_name}",
            pn_dn=ucs_rack_server, restrict_migration="no"
        )

    handler.add_mo(mo)
    handler.commit()
    mo = handler.query_dn(f"{organization}/ls-{service_profile_name}")

    # Save the service profile dn
    resource.service_profile_server_dn = f"{organization}/ls-{service_profile_name}"
    resource.name = service_profile_name
    resource.save()

    return "SUCCESS", f"Created service profile named {service_profile_name}", ""
