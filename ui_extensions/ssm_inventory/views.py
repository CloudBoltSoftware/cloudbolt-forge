import time
from time import sleep

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
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from utilities.decorators import json_view, dialog_view
from utilities.logger import ThreadLogger
from utilities.templatetags import helper_tags
from xui.ssm_inventory.forms import PatchEC2Form

logger = ThreadLogger(__name__)

XUI_PATH = path.dirname(path.abspath(__file__))

class TabDelegate(TabExtensionDelegate):
    def should_display(self):
        logger.debug(f"SSM Self: {self} ")
        logger.debug(f"SSM Server: {self.instance}")
        ssm_managed = get_ssm_managed(self.instance)
        logger.debug(f"SSM Managed: {ssm_managed}")
        return ssm_managed


@tab_extension(
    model=Server, title="Inventory", delegate=TabDelegate,
    description="Displays a list of guest apps"
)
def server_tab_ssm(request, obj_id):
    server = get_object_or_404(Server, pk=obj_id)

    return render(request, 'ssm_inventory/templates/server_tab.html', dict(
        server=server,
    ))


@json_view
def inventory_json(request, server_id):
    logger.debug(f"SSM Inventory: {request.__dict__}")
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)
    inventory = get_ssm_inventory(server)

    total_rows, display_rows, paged_inventory = data_tables_helper(request,
                                                                   inventory)

    return {
        "sEcho": int(request.GET.get("sEcho", 1)),
        "iTotalRecords": total_rows,
        "iTotalDisplayRecords": display_rows,
        "aaData": paged_inventory,
    }


def sort_list(inventory, column, descending=True):
    return sorted(inventory, key=lambda x: x[column], reverse=descending)


def filter_inventory(inventory, search):
    if not search:
        return inventory
    search = search.lower()
    filtered = []
    for item in inventory:
        if any(search in str(field).lower() for field in item):
            filtered.append(item)
    return filtered


def get_ssm_inventory(server):
    instance_id = server.ec2serverinfo.instance_id
    ssm = get_client(server, "ssm")
    # Retrieve the inventory for the instance - loop through until all results
    # are captured
    inventory_entries = []
    inventory = ssm.list_inventory_entries(
        InstanceId=instance_id,
        TypeName='AWS:Application'
    )
    inventory_entries.extend(loop_through_inventory(inventory["Entries"]))
    while 'NextToken' in inventory:
        next_token = inventory['NextToken']
        more_inventory = ssm.list_inventory_entries(
            InstanceId=instance_id,
            TypeName='AWS:Application',
            NextToken=next_token
        )
        inventory_entries.extend(
            loop_through_inventory(more_inventory["Entries"])
        )
        if 'NextToken' in more_inventory:
            inventory['NextToken'] = more_inventory['NextToken']
        else:
            inventory.pop('NextToken')
    return inventory_entries


def loop_through_inventory(inventory):
    rows = []
    for i in inventory:
        try:
            release = i["Release"]
        except KeyError:
            release = "-"
        rows.append([
            i["Name"],
            i["Version"],
            release
        ])
    return rows



def get_client(server, service):
    rh = server.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    region = server.ec2serverinfo.ec2_region
    client = wrapper.get_boto3_client(service, rh.serviceaccount,
                                          rh.servicepasswd, region)
    return client


def get_ssm_managed(server):
    if server.resource_handler.resource_technology.slug != "aws":
        return False
    instance_id = server.ec2serverinfo.instance_id
    ssm = get_client(server, "ssm")

    response = ssm.describe_instance_information(
        InstanceInformationFilterList=[
            {
                "key": "InstanceIds",
                "valueSet": [instance_id]
            }
        ]
    )
    if not response['InstanceInformationList']:
        return False
    return True


@dialog_view
def patch_ec2(request, server_id):
    logger.debug(f"Patch EC2: {request.__dict__}")
    logger.debug(f"server_id: {server_id}")
    profile = request.get_user_profile()
    action_url = reverse("ssm_inventory_patch_ec2", args=[server_id])
    server = get_object_or_404(Server, pk=server_id)
    initial = {
        "operation": "Install",
        "reboot_option": "RebootIfNeeded",
    }
    if request.method == "POST":
        form = PatchEC2Form(request.POST, initial=initial)
        if form.is_valid():
            operation, reboot_option = form.save()
            msg = (f"Patch EC2 with operation {operation} and reboot option "
                   f"{reboot_option}")
            logger.info(f"PatchEC2Form.save(): {msg}")
            # Here you would add the logic to perform the patch operation
            hook = get_cloudbolt_hook()
            job = hook.run_as_job(
                server=server, reboot_option=reboot_option, operation=operation,
            )[0]
            msg = format_html(
                _("Job {job_name} has been created to check rule(s).").format(
                    job_name=helper_tags.render_simple_link(job)
                )
            )
            messages.info(request, msg)
            return HttpResponseRedirect(request.META["HTTP_REFERER"])

    else:
        form = PatchEC2Form(initial=initial)
    return {
        "title": "Patch EC2 Instance",
        "form": form,
        "use_ajax": True,
        "action_url": action_url,
        "submit": "Start Patching",
    }


class PatchError(Exception):
    pass

def patch_ec2_instance(
    server,
    *,
    operation: str = "Install",                 # "Install" or "Scan"
    reboot_option: str = "RebootIfNeeded",      # "RebootIfNeeded" or "NoReboot"
    snapshot_id: str = None,          # Optional: record a Systems Manager snapshot ID
    comment: str = None,
    output_s3_bucket: str = None,     # Optional: S3 bucket for command output
    output_s3_prefix: str = None,
    cw_log_group: str = None,         # Optional: CloudWatch log group for command output
    timeout_seconds: int = 3600,
    poll_every_seconds: int = 10
):
    """
    Patches a single EC2 instance via SSM Patch Manager (AWS-RunPatchBaseline).

    Returns a dict with command metadata (always) and final invocation status (if wait=True).

    Requirements:
      - The instance must be SSM-managed: SSM agent running, reachable, and IAM role with SSM permissions attached.
      - The instance should have appropriate Patch Group tag or default baselines will apply.
      - Your caller identity must allow ssm:SendCommand and ssm:GetCommandInvocation.
    """
    instance_id = server.ec2serverinfo.instance_id
    region = server.ec2serverinfo.ec2_region
    operation = operation.capitalize()
    reboot_option = reboot_option if reboot_option in {"RebootIfNeeded", "NoReboot"} else "RebootIfNeeded"
    if operation not in {"Install", "Scan"}:
        raise ValueError("operation must be 'Install' or 'Scan'")

    ssm = get_client(server, "ssm")

    # Build Parameters for AWS-RunPatchBaseline
    params = {
        "Operation": [operation],
        "RebootOption": [reboot_option],
    }
    if snapshot_id:
        params["SnapshotId"] = [snapshot_id]

    send_kwargs = {
        "InstanceIds": [instance_id],
        "DocumentName": "AWS-RunPatchBaseline",
        "Parameters": params,
        "TimeoutSeconds": timeout_seconds,
    }
    if comment:
        send_kwargs["Comment"] = comment
    if output_s3_bucket:
        send_kwargs["OutputS3BucketName"] = output_s3_bucket
        if output_s3_prefix:
            send_kwargs["OutputS3KeyPrefix"] = output_s3_prefix
        # Region for S3 output defaults to the command's region; you can set OutputS3Region if needed.
        send_kwargs["OutputS3Region"] = region
    if cw_log_group:
        send_kwargs["CloudWatchOutputConfig"] = {
            "CloudWatchLogGroupName": cw_log_group,
            "CloudWatchOutputEnabled": True,
        }

    resp = ssm.send_command(**send_kwargs)
    command_id = resp["Command"]["CommandId"]

    result = {
        "command_id": command_id,
        "instance_id": instance_id,
        "region": region,
        "operation": operation,
        "reboot_option": reboot_option,
    }

    # Poll the command invocation until it reaches a terminal state
    terminal_statuses = {"Success", "Failed", "Cancelled", "TimedOut"}
    set_progress(f"Sent patch command {command_id} to instance {instance_id} "
                 f"in region {region}. Waiting for it to complete...")
    # Initial wait before polling to avoid immediate throttling
    sleep(15)
    while True:
        inv = ssm.get_command_invocation(
            CommandId=command_id, InstanceId=instance_id
        )
        status = inv.get("Status", "Unknown")
        result["invocation"] = {
            "status": status,
            "status_details": inv.get("StatusDetails"),
            "requested_date_time": inv.get("RequestedDateTime"),
            "execution_start_date_time": inv.get("ExecutionStartDateTime"),
            "execution_end_date_time": inv.get("ExecutionEndDateTime"),
            "standard_output_url": inv.get("StandardOutputUrl"),
            "standard_error_url": inv.get("StandardErrorUrl"),
            "response_code": inv.get("ResponseCode"),
            "command_plugins": inv.get("CommandPlugins"),
        }
        if status in terminal_statuses:
            if status != "Success":
                # Surface a helpful error, but still return all metadata
                raise PatchError(f"Patch command finished with status: "
                                 f"{status}. See CloudWatch/S3 or "
                                 f"'command_plugins' for details.")
            return result
        logger.debug(f"Patch command {command_id} on {instance_id} status: "
                     f"{status}. Waiting...")
        time.sleep(poll_every_seconds)


def get_cloudbolt_hook():
    try:
        hook = OrchestrationHook.objects.get(name="SSM Patch EC2 Server Hook")
    except OrchestrationHook.DoesNotExist:
        hook = register_cloudbolt_hook()
    return hook


def register_cloudbolt_hook():
    hook_info = {
        "name": "SSM Patch EC2 Server Hook",
        "description": "Hook for patching AWS EC2 Instances via SSM",
        "hook_point": "",
        "module": f"{XUI_PATH}/patch_hook.py",
    }
    return create_hook(**hook_info)


@tab_extension(
    model=Server, title="Patching", delegate=TabDelegate,
    description="Displays a list of guest patches available in SSM Patch Manager"
)
def server_tab_ssm_patches(request, obj_id):
    server = get_object_or_404(Server, pk=obj_id)

    return render(request, 'ssm_inventory/templates/server_patches.html', dict(
        server=server,
    ))


@json_view
def patch_json(request, server_id):
    logger.debug(f"SSM Patches: {request.__dict__}")
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)
    patches = list_instance_patches(server)

    total_rows, display_rows, paged_inventory = data_tables_helper(request,
                                                                   patches)

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


def list_instance_patches(server):
    """
    Return all patch records for a given EC2 instance managed by SSM Patch Manager.

    Parameters
    ----------
    server : Server
        The Server object representing the EC2 instance.

    Returns
    -------
    List[List]
        List of patch records, each represented as a list of fields:
        - Title
        - KBId
        - Classification
        - Severity
        - State
        - InstalledTime (formatted as MM/DD/YYYY or "-")

    Notes
    -----
    - The instance must be a *managed instance* in SSM (SSM Agent installed & online).
    - Required IAM permission: `ssm:DescribeInstancePatches`.
    """
    session_kwargs = {}

    ssm = get_client(server, "ssm")
    instance_id = server.ec2serverinfo.instance_id

    paginator = ssm.get_paginator("describe_instance_patches")
    page_iter = paginator.paginate(
        InstanceId=instance_id,
        Filters=[
            {
                "Key": "State",
                "Values": [
                    "INSTALLED",
                    "INSTALLED_OTHER",
                    "INSTALLED_PENDING_REBOOT",
                    "INSTALLED_REJECTED",
                    "MISSING",
                    "FAILED",
                    "AVAILABLE_SECURITY_UPDATES"
                ]
            }
        ],
        PaginationConfig={"PageSize": 50},
    )

    patches = []
    for page in page_iter:
        patches.extend(
            loop_through_patches(page.get("Patches", []))
        )
    return patches


def loop_through_patches(patches):
    rows = []
    for i in patches:
        installed_time = get_value_or_dash(i, "InstalledTime")
        if installed_time != "-":
            installed_time = installed_time.strftime("%m/%d/%Y")
        rows.append([
            get_value_or_dash(i, "Title"),
            get_value_or_dash(i, "KBId"),
            get_value_or_dash(i, "Classification"),
            get_value_or_dash(i, "Severity"),
            get_value_or_dash(i, "State"),
            installed_time,
        ])
    return rows


def get_value_or_dash(item, key):
    try:
        value = item[key]
    except KeyError:
        value = "-"
    return value