"""Views for the CloudWatch health dashboard XUI.

- cloudwatch_health_panel: @dashboard_extension that renders the card shell and
  the widget catalog. It makes no AWS call on render, so the main dashboard never
  blocks on CloudWatch.
- metrics_api: @json_view that returns the metric snapshot scoped to what the
  signed-in user may see (all AWS servers for super-admins; group servers
  otherwise). Reads the cached snapshot when fresh, else pulls live.
"""

import json

from django.shortcuts import render

from extensions.views import dashboard_extension
from infrastructure.models import Server
from utilities.decorators import json_view
from utilities.logger import ThreadLogger

from xui.cloudwatch_health import cache, constants
from xui.cloudwatch_health.api_wrapper import collect_for_servers

logger = ThreadLogger(__name__)


def _scoped_servers(profile):
    """AWS servers the user may see: all for super-admins, else group servers."""
    qs = Server.objects.filter(
        resource_handler__awshandler__isnull=False
    ).exclude(status="HISTORICAL").select_related("environment", "resource_handler", "group")
    if not profile.super_admin:
        qs = qs.filter(group__in=profile.get_groups())
    return qs


def _widget_catalog():
    """Widget definitions the front end uses to render charts."""
    return {
        "instance": constants.INSTANCE_METRICS,
        "ebs": constants.EBS_METRICS,
        "rds": constants.RDS_METRICS,
    }


@dashboard_extension
def cloudwatch_health_panel(request):
    """Render the dashboard card shell + widget catalog (no AWS call here)."""
    return render(request, "cloudwatch_health/templates/dashboard_panel.html", {
        "widget_catalog_json": json.dumps(_widget_catalog()),
    })


@json_view
def metrics_api(request):
    """Return the RBAC-scoped metric snapshot.

    json_view always responds 200; the front end branches on which key is
    present ("instances"/"rds" vs "error").
    """
    profile = request.get_user_profile()
    servers = _scoped_servers(profile)
    allowed_ids = set(servers.values_list("global_id", flat=True))
    include_rds = constants.RDS_ENABLED and (
        profile.super_admin or not constants.RDS_SUPER_ADMIN_ONLY
    )

    snapshot, age = cache.read_snapshot()
    if snapshot and cache.is_fresh(age):
        # Filter the all-servers cache down to this user's scope.
        instances = [i for i in snapshot.get("instances", []) if i.get("server_id") in allowed_ids]
        rds = snapshot.get("rds", []) if include_rds else []
        return {
            "instances": instances,
            "rds": rds,
            "generated": snapshot.get("generated"),
            "window_minutes": snapshot.get("window_minutes"),
            "skipped": snapshot.get("skipped") or {},
            "errors": snapshot.get("errors") or [],
            "source": "cache",
        }

    # No fresh cache → live pull (scoped to what the user can see).
    try:
        data = collect_for_servers(servers, include_rds=include_rds)
        data["source"] = "live"
        return data
    except Exception as err:
        logger.exception(f"Live CloudWatch pull failed: {err}")
        return {"error": f"Could not load CloudWatch metrics: {err}"}
