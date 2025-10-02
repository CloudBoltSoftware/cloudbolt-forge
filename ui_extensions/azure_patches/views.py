import time
from time import sleep
import re

import requests
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.translation import ugettext as _
import json
from os import path
from c2_wrapper import create_hook
from cbhooks.models import CloudBoltHook, OrchestrationHook
from common.methods import set_progress
from datetime import datetime
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from utilities.decorators import json_view, dialog_view
from azure.core.polling import LROPoller
from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client
from utilities.logger import ThreadLogger
from utilities.templatetags import helper_tags

logger = ThreadLogger(__name__)

XUI_PATH = path.dirname(path.abspath(__file__))
API_VERSION = "2024-04-01"


class TabDelegate(TabExtensionDelegate):
    def should_display(self):
        logger.debug(f"AZ Patch Self: {self} ")
        server = self.instance
        logger.debug(f"AZ Patch Server: {server}, type: {type(server)}, server_id: "
                     f"{server.id}")
        if server.resource_handler.resource_technology.slug != "azure_arm":
            logger.debug(f"Server is not an Azure Server, AZ Patch XUI tab "
                         f"will not be shown.")
            return False
        az_managed = az_agent_installed(server)
        logger.debug(f"AZ Patch Managed: {az_managed}")
        return az_managed


@tab_extension(
    model=Server, title="Patching", delegate=TabDelegate,
    description="Displays a list of available patches for this VM"
)
def server_tab_az_patches(request, obj_id):
    server = get_object_or_404(Server, pk=obj_id)

    return render(request, 'azure_patches/templates/server_patches.html', dict(
        server=server,
    ))


@json_view
def inventory_json(request, server_id):
    # logger.debug(f"AZ Patch Inventory: {request.__dict__}")
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)
    inventory = get_latest_patches(server)

    total_rows, display_rows, paged_inventory = data_tables_helper(request,
                                                                   inventory)

    return {
        "sEcho": int(request.GET.get("sEcho", 1)),
        "iTotalRecords": total_rows,
        "iTotalDisplayRecords": display_rows,
        "aaData": paged_inventory,
    }


def data_tables_helper(request, inventory):
    # Get pagination parameters from DataTables
    start = int(request.GET.get('iDisplayStart', 0))
    length = int(request.GET.get('iDisplayLength', 10))
    search = request.GET.get('sSearch', '')
    sort_column = int(request.GET.get('iSortCol_0', 0))
    sort_direction = request.GET.get('sSortDir_0', "asc")
    descending = sort_direction == "desc"

    filtered_inventory = filter_inventory(inventory, search)
    sorted_inventory = sort_list(filtered_inventory, sort_column, descending)
    paged_inventory = sorted_inventory[start:start + length]

    total_rows = len(inventory)
    display_rows = len(filtered_inventory)
    return total_rows, display_rows, paged_inventory


def filter_inventory(inventory, search):
    if not search:
        return inventory
    search = search.lower()
    filtered = []
    for item in inventory:
        if any(search in str(field).lower() for field in item):
            filtered.append(item)
    return filtered


def sort_list(inventory, column, descending=True):
    return sorted(inventory, key=lambda x: x[column], reverse=descending)


def az_agent_installed(server):
    try:
        instance_view = get_vm_instance_view(server)
        status = instance_view["vm_agent"]["statuses"][0]["display_status"]
        if status == "Ready":
            return True
        logger.debug(f"Azure VM Agent status is '{status}', so Azure patching "
                     f"is not available.")
    except Exception as e:
        logger.warning(f"Error retrieving VM instance view: {e}")
    return False


def get_resource_client(server):
    rh = server.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    client = wrapper.resource_client
    return client


def get_compute_client(server):
    rh = server.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    client = wrapper.compute_client
    return client


def build_vm_id(server):
    """
    Construct the full Azure VM ID from the subscription, resource group, and VM name.
    :param server: CloudBolt Server object representing the Azure VM
    :return: Full Azure VM ID string
    """
    rh = server.resource_handler.cast()
    subscription_id = rh.serviceaccount
    resource_group = server.azurearmserverinfo.resource_group
    vm_name = server.hostname
    vm_id = (f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
             f"/providers/Microsoft.Compute/virtualMachines/{vm_name}")
    return vm_id


def get_vm_instance_view(server):
    compute_client = get_compute_client(server)
    return compute_client.virtual_machines.instance_view(
        server.azurearmserverinfo.resource_group,
        server.hostname
    ).as_dict()


def get_latest_patches(server):
    """
    Read the *latest stored* patch assessment for a VM via ARM REST (no new scan).

    Returns:
        - patches: list of software patches (Windows/Linux fields differ)
      If no prior assessment exists, returns ([], {}).
    """
    base = "https://management.azure.com"
    scope = "https://management.azure.com/.default"
    kql = get_patch_kql(server)
    token = get_token(server, scope)
    body = {
        "subscriptions": [server.resource_handler.cast().serviceaccount],
        "query": kql,
        "options": {"resultFormat": "objectArray"}
    }
    result = _post_arg(base, token, body)
    patches = []
    for patch in result["data"]:
        props = patch["properties"]
        if server.os_family.name == "Windows":
            patch_data = (
                props.get("patchName", ""),
                ", ".join(props.get("classifications", "")),
                props.get("kbId", ""),
                camel_to_sentence(props.get("rebootBehavior", "")),
                format_date(props.get("publishedDateTime", "")),
            )
        else:
            patch_data = (
                props.get("patchName", ""),
                ", ".join(props.get("classifications", "")),
                props.get("version", ""),
            )
        patches.append(patch_data)
    return patches


def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%m%d%Y")
    except ValueError:
        return date_str


def camel_to_sentence(text: str) -> str:
    # Insert a space before each capital letter (except at the start)
    sentence = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
    # Lowercase everything, then capitalize the first letter
    return sentence.lower().capitalize()


def get_token(server, scope):
    cred = server.resource_handler.cast().get_api_wrapper().credentials
    return cred.get_token(scope).token


def _post_arg(base_url, token, body, timeout=60):
    url = (f"{base_url}/providers/Microsoft.ResourceGraph/resources"
           f"?api-version={API_VERSION}")
    resp = requests.post(
        url, json=body, headers={"Authorization": f"Bearer {token}"},
        timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()


def scan_vm_for_patches(server):
    compute_client = get_compute_client(server)
    poller = compute_client.virtual_machines.begin_assess_patches(
        resource_group_name=server.azurearmserverinfo.resource_group,
        vm_name=server.hostname,
    )
    return poller.result()


@dialog_view
def scan_for_patches(request, server_id):
    logger.debug(f"Patch EC2: {request.__dict__}")
    logger.debug(f"server_id: {server_id}")
    server = get_object_or_404(Server, pk=server_id)
    # Here you would add the logic to perform the patch operation
    hook = get_hook()
    job = hook.run_as_job(server=server, operation="scan_vm_for_patches")[0]
    msg = format_html(
        _("Job {job_name} has been created to scan for patches).").format(
            job_name=helper_tags.render_simple_link(job)
        )
    )
    messages.info(request, msg)
    return HttpResponseRedirect(request.META["HTTP_REFERER"])


@dialog_view
def apply_all_patches(request, server_id):
    logger.debug(f"Patch EC2: {request.__dict__}")
    logger.debug(f"server_id: {server_id}")
    server = get_object_or_404(Server, pk=server_id)
    # Here you would add the logic to perform the patch operation
    hook = get_hook()
    job = hook.run_as_job(server=server, operation="apply_all_vm_patches")[0]
    msg = format_html(
        _("Job {job_name} has been created to apply all patches.").format(
            job_name=helper_tags.render_simple_link(job)
        )
    )
    messages.info(request, msg)
    return HttpResponseRedirect(request.META["HTTP_REFERER"])


def get_hook():
    try:
        hook = OrchestrationHook.objects.get(name="Azure VM Patching")
    except OrchestrationHook.DoesNotExist:
        hook = register_hook()
    return hook


def register_hook():
    hook_info = {
        "name": "Azure VM Patching",
        "description": "Hook for scanning and patching Azure VMs",
        "hook_point": "",
        "module": f"{XUI_PATH}/actions/scan_for_patches.py",
    }
    return create_hook(**hook_info)


def get_patch_kql(server):
    rh = server.resource_handler.cast()
    subscription_id = rh.serviceaccount
    resource_group = server.azurearmserverinfo.resource_group
    vm_name = server.hostname
    return f"""
patchassessmentresources
| where type =~ "Microsoft.Compute/virtualMachines/patchAssessmentResults/softwarePatches"
| where id startswith "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}/patchAssessmentResults/latest/softwarePatches/"
| project id, properties
"""


def apply_all_vm_patches(
    server,
    *,
    # Reboot choices: "IfRequired", "Never", "Always"
    reboot_setting: str = "IfRequired",
    # LRO wait config
    poll_interval_seconds: int = 15,
    maximum_duration_iso8601: str = "PT2H",  # 2 hours
):
    """
    Install *all available* patches on the VM and block until the operation completes.

    Returns:
        (summary, raw_result_dict)
        - summary: { status, start_time, last_modified_time, installed_patch_count, failed_patch_count, ... }
        - raw_result_dict: full response from the service (OS-specific fields preserved)

    Raises:
        azure.core.exceptions.HttpResponseError on API errors
    """
    client = get_compute_client(server)
    resource_group = server.azurearmserverinfo.resource_group
    vm_name = server.hostname

    # For Windows: include all classifications.
    # For Linux: the most reliable way to get "everything" is to include all package names via "*".
    install_input = {
        "maximum_duration": maximum_duration_iso8601,
        "reboot_setting": reboot_setting,
        "windows_parameters": {
            "classifications_to_include": [
                "Critical", "Security", "UpdateRollup",
                "FeaturePack", "ServicePack", "Definition",
                "Tools", "Updates",
            ],
            # No KB excludes; install all
        },
        "linux_parameters": {
            # Install all packages available from the configured repos
            "package_name_masks_to_include": ["*"],
            # No excludes; install all
        },
    }

    # Start the LRO
    poller: LROPoller = client.virtual_machines.begin_install_patches(
        resource_group_name=resource_group,
        vm_name=vm_name,
        install_patches_input=install_input,  # dict is accepted by Track 2 SDKs
    )

    # Option A: just block until done
    # result = poller.result()

    # Option B: poll in a loop (lets you hook logs/telemetry if you want)
    while not poller.done():
        poller.wait(poll_interval_seconds)

    result = poller.result()
    result_dict = result.as_dict() if hasattr(result, "as_dict") else dict(result)

    # Shape typically includes 'status', 'started_at', 'last_modified_time', and a nested summary
    # Normalize a compact summary for convenience:
    summary = {
        "status": result_dict.get("status") or result_dict.get("installation_state"),
        "start_time": result_dict.get("started_at") or result_dict.get("start_time"),
        "last_modified_time": result_dict.get("last_modified_time") or result_dict.get("end_time"),
        "installed_patch_count": result_dict.get("installed_patch_count"),
        "excluded_patch_count": result_dict.get("excluded_patch_count"),
        "not_selected_patch_count": result_dict.get("not_selected_patch_count"),
        "pending_reboot": result_dict.get("reboot_status") in ("Required", "RequiredButNotAllowed"),
        "errors": result_dict.get("error_details") or result_dict.get("errors"),
        "activity_id": result_dict.get("installation_activity_id") or result_dict.get("assessment_activity_id"),
    }

    return summary, result_dict