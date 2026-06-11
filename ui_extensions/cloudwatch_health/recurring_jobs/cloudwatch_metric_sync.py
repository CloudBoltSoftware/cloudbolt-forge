"""Recurring Job: refresh the CloudWatch health snapshot cache.

Runs in an admin context (no request) and therefore collects metrics for ALL
AWS servers in CloudBolt. The dashboard views read this snapshot and filter it
to each user's RBAC scope, so live AWS calls never happen on page render.

Schedule it at roughly the dashboard window (e.g. every 5–10 minutes) under
Admin > scheduled jobs, then `supervisorctl restart all`.
"""

from common.methods import set_progress
from infrastructure.models import Server
from utilities.logger import ThreadLogger

from xui.cloudwatch_health import cache, constants
from xui.cloudwatch_health.api_wrapper import collect_for_servers

logger = ThreadLogger(__name__)


def run(job=None, *args, **kwargs):
    servers = Server.objects.filter(
        resource_handler__awshandler__isnull=False
    ).exclude(status="HISTORICAL").select_related(
        "environment", "resource_handler", "group"
    )

    count = servers.count()
    set_progress(f"Collecting CloudWatch metrics for {count} AWS server(s)")

    data = collect_for_servers(servers, include_rds=constants.RDS_ENABLED)
    cache.write_snapshot(data)

    n_instances = len(data.get("instances", []))
    skipped = data.get("skipped") or {}
    errors = data.get("errors") or []

    msg = (
        f"Cached CloudWatch snapshot: {n_instances} instance(s), "
        f"{len(data.get('rds', []))} RDS instance(s)."
    )
    if skipped:
        skip_bits = ", ".join(
            f"{reason}={len(hosts)} (e.g. {hosts[0]})" for reason, hosts in skipped.items()
        )
        msg += f" Skipped: {skip_bits}."
    if errors:
        msg += f" Errors: {errors[0]}" + (f" (+{len(errors) - 1} more)" if len(errors) > 1 else "")

    logger.info(msg)
    # An empty snapshot from a non-empty fleet means misconfig (region/instance
    # id mapping) or failed CloudWatch calls (handler IAM) — warn, don't claim
    # clean success.
    if count and n_instances == 0:
        return "WARNING", "", msg
    return "SUCCESS", msg, ""
