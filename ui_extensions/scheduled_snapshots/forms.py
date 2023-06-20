import croniter
import datetime
import pycron

from django.forms import ValidationError, CharField, widgets
from django.utils.html import format_html

from common.fields import form_field_for_cf
from common.forms import C2Form
from infrastructure.models import CustomField, Server, ServerSnapshot
from utilities import events
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


class EditServerMaxSnapshotsParameterForm(C2Form):
    """
    Form for editing the value of the Maximum # of Snapshots Parameter on the Server
    """
    def __init__(self, *args, **kwargs):
        from xui.scheduled_snapshots.views import MAX_TIP

        self.server = kwargs.pop("server")
        self.field = CustomField.objects.get(name="scheduled_snapshot_maximum")

        super().__init__(*args, **kwargs)

        self.fields["value"] = form_field_for_cf(self.field, server=self.server)
        self.fields["value"].help_text = MAX_TIP

    def save(self, profile):
        new_value = self.cleaned_data["value"]
        if new_value == "":
            # The text field was empty, but None is handled better than empty string
            new_value = None

        self.server.update_cf_value(self.field, new_value, profile)
        if new_value:
            msg = f"Maximum # of Snapshots was set to {new_value}."
        else:
            msg = "Maximum # of Snapshots was removed for this Server. Will default to Recurring Job value"

        return msg


class EditServerSnapshotScheduleParameterForm(C2Form):
    """
    Form for editing the value of the Snapshot Schedule Parameter on the Server
    """

    def __init__(self, *args, **kwargs):

        self.server = kwargs.pop("server")
        self.field = CustomField.objects.get(name="scheduled_snapshot_schedule")

        super().__init__(*args, **kwargs)

        self.fields["value"] = form_field_for_cf(self.field, server=self.server)
        self.fields["value"].help_text = (
            "Cron-style string that specifies when to take a snapshot of this Server. The minutes "
            "value (the first one) must be 0 to match the Recurring Job running only on the hour"
        )

    def clean_value(self):
        """
        Slight improvement to UX by helping them enter a valid cron-format value
        """
        data = self.cleaned_data["value"]

        if data:
            # Make sure both pycron & croniter can parse this cron schedule. Each chokes on different
            # formats - ex. croniter does not like "@ @ @ @ @". pycron can't really deal with that
            # either, it just doesn't raise an exception, so check both here.
            try:
                pycron.is_now(data)
            except ValueError as err:
                raise ValidationError(str(err).capitalize())
            try:
                croniter.croniter(data, datetime.datetime.now())
            except (ValueError, KeyError) as err:
                raise ValidationError(str(err).capitalize())

            # Also make sure it's only scheduled to run on the hour, to match Recurring Job run-time.
            # Apparently it's valid to make the 1st piece multiple 0s (e.g., 00), so take that into account
            minute = data.split(" ")[0]
            if not int(minute) == 0:
                raise ValidationError(
                    "Only schedules with a 0 minute are valid, since the Recurring Job only "
                    "runs on the hour"
                )

        return data

    def save(self, profile):
        new_value = self.cleaned_data["value"]

        self.server.update_cf_value(self.field, new_value, profile)
        if new_value:
            msg = f"Snapshot Schedule was set to {new_value}."
        else:
            msg = "Snapshot Schedule was removed for this Server. No snapshots will be automatically taken"

        return msg


class ServerCreateSnapshotRespectMaxForm(C2Form):
    """
    Form for creating a manual snapshot

    Note: this is very similar to the usual ServerCreateSnapshotForm, but changes
    the behavior around deleting old snapshots to allow more than one to persist
    """
    server_id = CharField(widget=widgets.HiddenInput())
    name = CharField(label="Name", max_length=50)
    description = CharField(
        label="Description",
        max_length=256,
        widget=widgets.Textarea(attrs={"rows": 5, "cols": 80}),
        required=False,
    )

    def save(self, profile):
        server_id = self.cleaned_data["server_id"]
        snapshot_name = self.cleaned_data.get("name")
        snapshot_desc = self.cleaned_data.get("description")
        server = Server.objects.get(id=server_id)
        rh = server.resource_handler.cast()
        success = False

        try:
            # The new snapshot is created before deleting the old ones because we want to ensure
            # that the new one is successfully created before deleting the old.
            new_snapshot = rh.create_snapshot(server, snapshot_name, snapshot_desc)
        except Exception:
            msg = "Server failed to create snapshot"
            logger.exception(msg)
        else:
            success = True
            msg = format_html(
                "Server snapshot {snapshot} created.",
                snapshot=new_snapshot.name_with_tooltip,
            )
            events.add_server_event("MODIFICATION", server, msg, profile)

            # If there is a maximum # of snapshots set and that many already exist, delete
            # older ones. Otherwise, leave them all
            max_snapshots = server.scheduled_snapshot_maximum
            if max_snapshots:
                num_snapshots = ServerSnapshot.objects.filter(server=server).count()
                if num_snapshots > max_snapshots:
                    snapshots = list(ServerSnapshot.objects.filter(server=server).order_by("-date_created"))
                    snapshots_to_delete = snapshots[max_snapshots:]
                    job_created_msg = server.create_delete_snapshots_job(
                        profile, snapshots_to_delete
                    )
                    msg = format_html("{}{}", msg, job_created_msg)

        return success, msg
