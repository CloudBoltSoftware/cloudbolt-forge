from datetime import datetime
import pycron

from django.template.defaultfilters import pluralize
from django.utils.html import format_html
from django.utils.translation import ugettext as _

from common.methods import set_progress
from infrastructure.models import Server, ServerSnapshot
from utilities import events
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, **kwargs):
    """
    Check for any Servers that are scheduled to have a Snapshot taken at this time. For each, take a snapshot
    (be careful just in case someone somehow configured a Server that doesn't support taking snapshots).
    Then, check whether the maximum # of snapshots has been exceeded for that Server and, if so, delete
    the oldest snapshot to return to only having the maximum # (e.g., if the max is 3 and we take a 4th,
    delete one so we're back to 3). Note that the snapshots considered here are only those created by
    CB; we do not discover snapshots that exist on the RH but were created separately.
    """
    now = datetime.now()
    snapshot_name = str(now)
    snapshot_desc = f"Scheduled snapshot taken by Recurring Job at {now}"
    # If there's no default value for the Action Input yet, go with 3
    default_max_snapshots = int("{{ snapshot_maximum }}" or 3)

    set_progress(f"Searching for Servers that are scheduled to have their snapshot taken now ({now})")
    # Only consider ACTIVE servers (trying to take snapshots of Servers in other states might not go well)
    # that have an appropriate value for the schedule parameter and whose RH can manage snapshots
    active_servers = Server.objects.filter(status="ACTIVE")
    servers = [
        s for s in active_servers if
        s.resource_handler and s.resource_handler.cast().can_manage_snapshots
        and s.scheduled_snapshot_schedule and pycron.is_now(s.scheduled_snapshot_schedule, now)
    ]

    if servers:
        servers_str = ", ".join([svr.hostname for svr in servers])
        set_progress(
            f"Taking a snapshot of {len(servers)} Server{pluralize(len(servers))}: {servers_str}"
        )
    else:
        set_progress("No Servers to take a snapshot of right now")

    failures = []
    for server in servers:
        # Modified from ServerCreateSnapshotForm
        rh = server.resource_handler.cast()
        try:
            new_snapshot = rh.create_snapshot(server, snapshot_name, snapshot_desc)
        except Exception:
            msg = f"Server {server.hostname} failed to create snapshot"
            logger.exception(msg)
            failures.append(server.hostname)
        else:
            msg = format_html(
                _("Server snapshot {snapshot} created."),
                snapshot=new_snapshot.name_with_tooltip,
            )
            events.add_server_event("MODIFICATION", server, msg)
            set_progress(f"Successfully created snapshot for {server.hostname}")

            # If the Server has its own max set, use that. Otherwise, default to the Action Input value
            max_snapshots = server.scheduled_snapshot_maximum
            if max_snapshots is None:
                max_snapshots = default_max_snapshots
            num_snapshots = ServerSnapshot.objects.filter(server=server).count()
            if num_snapshots > max_snapshots:
                snapshots = list(ServerSnapshot.objects.filter(server=server).order_by("-date_created"))
                snapshots_to_delete = snapshots[max_snapshots:]
                num_snapshots_to_delete = "one" if len(snapshots_to_delete) == 1 else len(snapshots_to_delete)
                set_progress(f"With {num_snapshots} snapshots, {server.hostname} has exceeded the "
                             f"max of {max_snapshots}. Deleting the oldest {num_snapshots_to_delete}")
                # The None is for profile, since this is run automatically instead of by a User
                job_created_msg = server.create_delete_snapshots_job(
                    None, snapshots_to_delete
                )
                logger.info(job_created_msg)

    if failures:
        msg = f"Taking the snapshot failed for at least 1 Server: {', '.join(failures)}"
        return "FAILURE", "", msg
