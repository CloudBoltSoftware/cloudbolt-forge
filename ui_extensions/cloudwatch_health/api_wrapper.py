"""CloudWatch data access for the health dashboard.

Single home for all boto3 CloudWatch/EC2/RDS calls so views.py and the recurring
job share one implementation. Given a set of CloudBolt Server objects, it groups
them by (AWS handler, region), batches get_metric_data calls, and returns a
normalized snapshot the front end renders with Highcharts.

Imported as: from xui.cloudwatch_health.api_wrapper import collect_for_servers
"""

import datetime
from collections import defaultdict

from utilities.logger import ThreadLogger

from xui.cloudwatch_health import constants

logger = ThreadLogger(__name__)

# get_metric_data accepts at most 500 MetricDataQueries per call.
_MAX_QUERIES_PER_CALL = 500


def _server_aws_meta(server):
    """Return (handler, region, instance_id, skip_reason) for a server.

    skip_reason is None when the server is usable; otherwise it names exactly
    why the server cannot be collected (so the sync job can surface it instead
    of silently producing an empty snapshot).
    """
    handler = server.resource_handler.cast() if server.resource_handler else None
    if not handler or handler.__class__.__name__ != "AWSHandler":
        return None, None, None, "not_aws_handler"
    instance_id = server.resource_handler_svr_id
    if not instance_id or not str(instance_id).startswith("i-"):
        return None, None, None, "missing_or_invalid_instance_id"
    region = getattr(server.environment, "aws_region", None) or getattr(handler, "aws_region", None)
    if not region:
        return None, None, None, "missing_region"
    return handler, region, instance_id, None


def _run_metric_data(cw, queries, start, end):
    """Execute get_metric_data over queries (chunked + paginated).

    Returns {query_id: latest_value_or_None}.
    """
    results = {}
    for i in range(0, len(queries), _MAX_QUERIES_PER_CALL):
        chunk = queries[i:i + _MAX_QUERIES_PER_CALL]
        token = None
        while True:
            params = {
                "MetricDataQueries": chunk,
                "StartTime": start,
                "EndTime": end,
                "ScanBy": "TimestampDescending",  # Values[0] == most recent
            }
            if token:
                params["NextToken"] = token
            resp = cw.get_metric_data(**params)
            for r in resp.get("MetricDataResults", []):
                values = r.get("Values") or []
                # Keep the first (latest) non-null value seen across pages.
                if r["Id"] not in results and values:
                    results[r["Id"]] = values[0]
            token = resp.get("NextToken")
            if not token:
                break
    return results


def _instance_volumes(handler, region, instance_ids):
    """Map {instance_id: [volume_id, ...]} for EBS volumes attached to instances."""
    ec2 = handler.get_boto3_client(region, "ec2")
    mapping = defaultdict(list)
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate(
        Filters=[{"Name": "attachment.instance-id", "Values": instance_ids}]
    ):
        for vol in page.get("Volumes", []):
            for att in vol.get("Attachments", []):
                iid = att.get("InstanceId")
                if iid:
                    mapping[iid].append(vol["VolumeId"])
    return mapping


def _collect_group(handler, region, server_meta, start, end, period):
    """Collect all per-instance + EBS metrics for one (handler, region) group.

    server_meta: {instance_id: {"hostname", "server_id", "group"}}
    Returns a list of per-instance dicts.
    """
    cw = handler.get_boto3_client(region, "cloudwatch")
    instance_ids = list(server_meta.keys())

    queries = []
    registry = {}  # query_id -> (instance_id, widget_key)
    qn = 0

    def add_query(scope_id, widget):
        nonlocal qn
        qid = f"m{qn}"
        qn += 1
        dim_name = "VolumeId" if widget["namespace"] == "AWS/EBS" else "InstanceId"
        queries.append({
            "Id": qid,
            "MetricStat": {
                "Metric": {
                    "Namespace": widget["namespace"],
                    "MetricName": widget["metric"],
                    "Dimensions": [{"Name": dim_name, "Value": scope_id}],
                },
                "Period": period,
                "Stat": widget["stat"],
            },
            "ReturnData": True,
        })
        return qid

    # Per-instance native + agent metrics.
    for iid in instance_ids:
        for widget in constants.INSTANCE_METRICS:
            registry[add_query(iid, widget)] = (iid, widget["key"])

    # EBS metrics scoped to attached volumes.
    vol_map = {}
    try:
        vol_map = _instance_volumes(handler, region, instance_ids)
    except Exception as err:
        logger.warning(f"describe_volumes failed for {handler.name}/{region}: {err}")
    vol_to_instance = {}
    for iid, vols in vol_map.items():
        for vol in vols:
            vol_to_instance[vol] = iid
            for widget in constants.EBS_METRICS:
                registry[add_query(vol, widget)] = (vol, widget["key"])

    values = _run_metric_data(cw, queries, start, end)

    # Assemble per-instance output.
    out = {}
    for iid, meta in server_meta.items():
        out[iid] = {
            "instance_id": iid,
            "hostname": meta["hostname"],
            "server_id": meta["server_id"],
            "group": meta["group"],
            "power_status": meta.get("power_status", ""),
            "region": region,
            "metrics": {},   # widget_key -> value
            "volumes": {},   # volume_id -> {widget_key: value}
        }

    for qid, (scope_id, key) in registry.items():
        val = values.get(qid)
        if scope_id in out:                       # instance-scoped metric
            out[scope_id]["metrics"][key] = val
        elif scope_id in vol_to_instance:         # volume-scoped (EBS) metric
            iid = vol_to_instance[scope_id]
            out[iid]["volumes"].setdefault(scope_id, {})[key] = val

    return list(out.values())


def _collect_rds(handler, region):
    """Collect RDS metrics for every DB instance in this handler/region."""
    rds = handler.get_boto3_client(region, "rds")
    cw = handler.get_boto3_client(region, "cloudwatch")
    db_ids = []
    try:
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_ids.append(db["DBInstanceIdentifier"])
    except Exception as err:
        logger.warning(f"describe_db_instances failed for {handler.name}/{region}: {err}")
        return []
    if not db_ids:
        return []

    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(minutes=constants.DEFAULT_WINDOW_MINUTES)
    queries, registry, qn = [], {}, 0
    for db_id in db_ids:
        for widget in constants.RDS_METRICS:
            qid = f"r{qn}"
            qn += 1
            registry[qid] = (db_id, widget["key"])
            queries.append({
                "Id": qid,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/RDS",
                        "MetricName": widget["metric"],
                        "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": db_id}],
                    },
                    "Period": constants.DEFAULT_PERIOD_SECONDS,
                    "Stat": widget["stat"],
                },
                "ReturnData": True,
            })
    values = _run_metric_data(cw, queries, start, end)
    out = {db_id: {"db_id": db_id, "region": region, "metrics": {}} for db_id in db_ids}
    for qid, (db_id, key) in registry.items():
        out[db_id]["metrics"][key] = values.get(qid)
    return list(out.values())


def collect_for_servers(servers, include_rds=False):
    """Build a metric snapshot for the given CloudBolt Server queryset/list.

    Returns:
      {
        "generated": ISO-8601 str,
        "window_minutes": int,
        "instances": [ {instance_id, hostname, server_id, group, region,
                         metrics{key:val}, volumes{vol:{key:val}}}, ... ],
        "rds": [ {db_id, region, metrics{key:val}}, ... ],
      }
    """
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(minutes=constants.DEFAULT_WINDOW_MINUTES)
    period = constants.DEFAULT_PERIOD_SECONDS

    # Group servers by (handler, region). Track skips/errors so callers can
    # surface WHY a snapshot came back empty instead of reporting silent success.
    groups = defaultdict(dict)
    handler_by_key = {}
    skipped = defaultdict(list)   # reason -> [hostnames]
    errors = []                   # human-readable per-group collection failures
    for server in servers:
        handler, region, iid, reason = _server_aws_meta(server)
        if reason:
            skipped[reason].append(server.hostname)
            continue
        key = (handler.id, region)
        handler_by_key[key] = handler
        groups[key][iid] = {
            "hostname": server.hostname,
            "server_id": server.global_id,
            "group": server.group.name if server.group else "",
            "power_status": server.power_status or "",
        }

    if skipped:
        summary = "; ".join(
            f"{reason}: {len(hosts)} (e.g. {', '.join(hosts[:3])})"
            for reason, hosts in skipped.items()
        )
        logger.warning(f"CloudWatch sync skipped servers — {summary}")

    instances = []
    for key, server_meta in groups.items():
        handler = handler_by_key[key]
        region = key[1]
        try:
            instances.extend(_collect_group(handler, region, server_meta, start, end, period))
        except Exception as err:
            msg = f"{handler.name}/{region}: {err}"
            errors.append(msg)
            logger.exception(f"CloudWatch collection failed for {msg}")
            continue

    rds = []
    if include_rds:
        seen = set()
        for (handler_id, region), handler in handler_by_key.items():
            if (handler_id, region) in seen:
                continue
            seen.add((handler_id, region))
            try:
                rds.extend(_collect_rds(handler, region))
            except Exception as err:
                errors.append(f"RDS {handler.name}/{region}: {err}")
                logger.exception(f"RDS collection failed for {handler.name}/{region}: {err}")

    return {
        "generated": end.replace(tzinfo=datetime.timezone.utc).isoformat(),
        "window_minutes": constants.DEFAULT_WINDOW_MINUTES,
        "instances": instances,
        "rds": rds,
        "skipped": {reason: hosts for reason, hosts in skipped.items()},
        "errors": errors,
    }
