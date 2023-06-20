import croniter
import datetime
import os

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cbhooks.models import CloudBoltHook
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.forms import ServerRevertToSnapshotForm
from infrastructure.models import Server, ServerSnapshot, CustomField
from jobs.models import RecurringJob
from utilities.decorators import dialog_view
from utilities.permissions import get_cb_permissions, server_permission
from utilities.templatetags.helper_tags import portal_label, when, render_list
from xui.scheduled_snapshots.forms import (
    EditServerMaxSnapshotsParameterForm,
    EditServerSnapshotScheduleParameterForm,
    ServerCreateSnapshotRespectMaxForm,
)


MAX_TIP = (
    "The number of scheduled snapshots to take of this Server before beginning to delete the oldest. "
    "Optionally overrides the default set on the Recurring Job"
)


class ScheduledSnapshotsTabDelegate(TabExtensionDelegate):
    def should_display(self):
        """
        Only show the Scheduled Snapshots Server tab if the Server's RH can manage snapshots and the
        User has the server.manage_snapshots permission on the Server
        """
        rh = self.instance.resource_handler
        if rh:
            rh = rh.cast()
            if rh.can_manage_snapshots:
                if "server.manage_snapshots" in get_cb_permissions(self.viewer, self.instance):
                    return True

        return False


def get_or_create_required_objects():
    """
    Creates the related objects (parameters, Recurring Job) that are needed to support this
    UI Extension, if needed. If they already exist, just gets them and returns whatever's needed
    """
    CustomField.objects.get_or_create(
        name='scheduled_snapshot_schedule', type='STR',
        defaults={'label': 'Schedule for Snapshots',
                  'description': (
                      'Cron-style timing to take a snapshot of a Server. Only intended for use with the Scheduled '
                      'Snapshots UI Extension and its associated "Take Scheduled Snapshots" Recurring Job'
                  )})
    CustomField.objects.get_or_create(
        name='scheduled_snapshot_maximum', type='INT',
        defaults={'label': 'Maximum # of Snapshots',
                  'description': (
                        'The number of scheduled snapshots to take of a Server before beginning to delete '
                        'the oldest. Optionally overrides the default set on the Recurring Job. Only intended '
                        'for use with the Scheduled Snapshots UI Extension and its associated "Take Scheduled '
                        'Snapshots" Recurring Job'
                  )})

    from c2_wrapper import create_hook
    from initialize.create_objects import create_recurring_job
    # Use the existing helper methods, but only if the objects don't already exist
    action = CloudBoltHook.objects.filter(name="Take Scheduled Snapshots").first()
    if not action:
        rec_job_action_dict = {
            "name": "Take Scheduled Snapshots",
            "description": "Plug-in to support the Recurring Job that takes snapshots that have been scheduled",
            "hook_point": None,
            "module": os.path.join(settings.PROSERV_DIR, "xui/scheduled_snapshots/actions/take_scheduled_snapshots.py"),
            "inputs": [
                {
                    "name": "snapshot_maximum",
                    "label": "Maximum # of Snapshots",
                    "description": (
                        "The number of scheduled snapshots to take of a Server before beginning to delete "
                        "the oldest. Can be overridden by the value set on a specific Server"
                    ),
                    "type": "INT",
                    "namespace": "action_inputs",
                }
            ],
        }
        create_hook(**rec_job_action_dict)
    rec_job = RecurringJob.objects.filter(name="Take Scheduled Snapshots").first()
    if not rec_job:
        rec_job_dict = {
            "name": "Take Scheduled Snapshots",
            "enabled": True,
            "description": (
                "This Recurring Job enables scheduling snapshots to be taken of Servers automatically at a "
                "certain time of day. To use this feature, go to a Server's details page and configure a "
                "snapshot schedule and potentially override the maximum # of snapshots on the Scheduled "
                "Snapshots tab added by the UI Extension to supported Servers."
                "When the action runs it will look for Servers with a schedule set that indicates a snapshot "
                "should be taken during that hour, then generate a snapshot for each. It will also check "
                "whether each such Server has reached its maximum # of snapshots, either as set on that "
                "individual Server or per the default on this Recurring Job, and, if so, delete the oldest "
                "snapshot known to CloudBolt in order to respect that maximum. "
                "CloudBolt will use its own server time to judge whether it is the right time to take a "
                "snapshot, so make sure you know what time it is on the CB server and that the timezone is right. "
                "Also note that this Recurring Job is expected to be run "
                "every hour on the hour. If it is run on a different schedule, that will impact "
                "when snapshots are taken. The snapshot will only happen if the job runs "
                "during the hour when a snapshot is scheduled."
            ),
            "type": "recurring_action",
            "hook_name": "Take Scheduled Snapshots",
            # Once/hour at the beginning of the hour
            "schedule": "0 * * * *",
        }
        rec_job = create_recurring_job(rec_job_dict)
    return rec_job


@tab_extension(model=Server, title="Scheduled Snapshots", description="Manage scheduled snapshots",
               delegate=ScheduledSnapshotsTabDelegate)
def server_scheduled_snapshots_tab(request, obj_id):
    """
    Generates the Server tab for scheduling and managing snapshots.
    """
    rec_job = get_or_create_required_objects()

    server = Server.objects.get(id=obj_id)
    rh = server.get_resource_handler()
    details = rh.tech_specific_server_details(server)

    portal_lbl = portal_label(context={"request": request})
    infotip_text = f"All snapshots currently on the Server that have been created with {portal_lbl}"
    try:
        iter = croniter.croniter(server.scheduled_snapshot_schedule, datetime.datetime.now())
        next_time = iter.get_next(datetime.datetime)
    except (AttributeError, ValueError, KeyError) as err:
        # If something goes wrong just don't show this info because that most likely means we don't
        # have a schedule set
        next_snapshot = None
    else:
        next_snapshot = when(next_time)

    return render(request, "scheduled_snapshots/templates/server_tab.html",
                  {"server": server, "details": details, "portal_lbl": portal_lbl, "infotip_text": infotip_text,
                   "max_tip": MAX_TIP, "rec_job": rec_job, "next_snapshot": next_snapshot})


@dialog_view
def configure_snapshot_schedule(request, server_id):
    """
    Configure a value for the Snapshot Schedule for a Server by editing the corresponding
    Parameter's value
    """
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)

    if request.method == "GET":
        form = EditServerSnapshotScheduleParameterForm(server=server)

    else:
        form = EditServerSnapshotScheduleParameterForm(request.POST, server=server)
        if form.is_valid():
            msg = form.save(profile)
            messages.success(request, msg)
            return HttpResponseRedirect(reverse("server_detail", args=[server_id]))

    return {
        "title": _('Edit Snapshot Schedule on Server "{server}"').format(server=server),
        "form": form,
        "server": server,
        "action_url": reverse("configure_snapshot_schedule", args=[server_id]),
        "submit": _("Save"),
    }


@dialog_view
def configure_snapshot_max(request, server_id):
    """
    Configure a value for the Maximum # of Snapshots for a Server by editing the corresponding
    Parameter's value
    """
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)

    if request.method == "GET":
        form = EditServerMaxSnapshotsParameterForm(server=server)

    else:
        form = EditServerMaxSnapshotsParameterForm(request.POST, server=server)
        if form.is_valid():
            msg = form.save(profile)
            messages.success(request, msg)
            return HttpResponseRedirect(reverse("server_detail", args=[server_id]))

    return {
        "title": _('Edit Maximum # of Snapshots on Server "{server}"').format(server=server),
        "form": form,
        "server": server,
        "action_url": reverse("configure_snapshot_max", args=[server_id]),
        "submit": _("Save"),
    }


@dialog_view
@server_permission("server.manage_snapshots")
def server_revert_to_specific_snapshot(request, server_id, snapshot_id):
    """
    View for reverting a server to a particular snapshot

    Note: this is very similar to the usual server_revert_to_snapshot, but supports
    being run on a specific snapshot instead of just the newest. The code is copied
    rather than refactored so this XUI can work on older versions of CB
    """
    snapshot = ServerSnapshot.objects.filter(server_id=server_id, id=snapshot_id).first()
    prompt = format_html(
        _("Revert VM to snapshot {snapshot}?"),
        snapshot=snapshot.get_name_with_date_created(),
    )
    info = _(
        "The current disk and memory states of the VM will be lost. The "
        "disk state will be replaced with what existed when the snapshot "
        "was taken."
    )
    content = format_html("<p>{}</p> <p>{}</p>", prompt, info)

    if request.method == "POST":
        profile = request.get_user_profile()
        form = ServerRevertToSnapshotForm(request.POST)

        if form.is_valid():
            success, msg = form.save(profile)
            if success:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)
            return HttpResponseRedirect(reverse("server_detail", args=[server_id]))

    else:
        form = ServerRevertToSnapshotForm(
            initial={"server_id": server_id, "snapshot_id": snapshot_id}
        )

    return {
        "title": _("Revert to Snapshot"),
        "content": content,
        "form": form,
        "use_ajax": True,
        "action_url": reverse("server_revert_to_specific_snapshot", args=[server_id, snapshot_id]),
        "submit": _("Revert"),
    }


@dialog_view
@server_permission("server.manage_snapshots")
def server_create_snapshot_respect_max(request, server_id):
    """
    View for creating a new snapshot on a server

    Dialog asks for confirmation then runs synchronous creation of new
    snapshot, then potentially starts a job to delete old ones asynchronously
    if there is a maximum set and it has been exceeded

    Note: this is very similar to the usual server_create_snapshot, but changes
    the behavior around deleting old snapshots to allow more than one to persist
    """
    server = get_object_or_404(Server, pk=server_id)
    content = mark_safe(
        _(
            "Create new snapshot of VM at the current location? "
            "This action allows you to save the state of the server "
            "so it is possible to revert to it at a later time."
        )
    )

    # If there is a maximum # of snapshots set and that many already exist, delete
    # older ones. Otherwise, leave them all
    max_snapshots = server.scheduled_snapshot_maximum
    if max_snapshots:
        num_snapshots = ServerSnapshot.objects.filter(server=server).count()
        if num_snapshots >= max_snapshots:
            snapshots = list(ServerSnapshot.objects.filter(server=server).order_by("-date_created"))
            snapshots_to_delete = snapshots[(max_snapshots - 1):]
            warning = format_html(
                _(
                    "After the snapshot is created the following snapshots will be "
                    "permanently deleted:\n{snapshots}"
                ),
                snapshots=render_list(
                    [snap.get_name_with_date_created() for snap in snapshots_to_delete]
                ),
            )
            content += format_html(
                """
                <div class="alert alert-warning">
                  <p>
                        {warning}
                  </p>
                </div>""",
                warning=warning,
            )

    if request.method == "POST":
        profile = request.get_user_profile()
        form = ServerCreateSnapshotRespectMaxForm(request.POST)

        if form.is_valid():
            success, msg = form.save(profile)
            if success:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)
            return HttpResponseRedirect(reverse("server_detail", args=[server_id]))

    else:
        form = ServerCreateSnapshotRespectMaxForm(initial={"server_id": server_id})

    return {
        "title": _("Create Server Snapshot"),
        "content": content,
        "form": form,
        "use_ajax": True,
        "submit": _("Submit"),
        "action_url": reverse("server_create_snapshot_respect_max", args=[server_id]),
    }
