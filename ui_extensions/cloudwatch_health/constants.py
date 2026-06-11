"""Configuration + widget catalog for the CloudWatch health dashboard XUI.

The Resource Handler is intentionally NOT hardcoded: handler + region are
derived per server (tenant/user/group scoped). Everything else the views and the
recurring job need is here so there are no magic values scattered in code.

Each widget definition drives both the CloudWatch query (namespace/metric/stat)
and how charts.js renders it (chart type/unit). Metric names in the CWAgent
group must match infosys/cloudwatch_agent/cw_agent_config.json.
"""

# ── Time window ──────────────────────────────────────────────────────────────
# Matches the console default (last 1h, 5-minute period).
DEFAULT_WINDOW_MINUTES = 60
DEFAULT_PERIOD_SECONDS = 300

# ── RBAC ─────────────────────────────────────────────────────────────────────
# Super-admins see all AWS servers in CB; regular users see only servers in
# their group(s). This flag does NOT hide the card from regular users — it only
# controls whether the optional RDS section (which is account/region wide, not
# server-scoped) is shown. Keep RDS to admins since it isn't group-scoped.
RDS_ENABLED = True
RDS_SUPER_ADMIN_ONLY = True

# ── Cache ────────────────────────────────────────────────────────────────────
# Where the recurring job writes the pre-computed metric snapshot. Views read
# this first and fall back to a live pull if it's missing/stale.
CACHE_DIR = "/var/opt/cloudbolt/proserv/cached_xui_data/cloudwatch_health"
CACHE_FILE = "snapshot.json"
# Snapshot older than this (seconds) is considered stale → live refresh.
CACHE_MAX_AGE_SECONDS = 900

# ── Widget catalog ───────────────────────────────────────────────────────────
# Native EC2 metrics (no agent). Queried with a single {InstanceId} dimension.
EC2_METRICS = [
    {"key": "cpu", "label": "CPU Utilization", "namespace": "AWS/EC2",
     "metric": "CPUUtilization", "stat": "Average", "unit": "%", "chart": "gauge"},
    {"key": "status_failed", "label": "StatusCheckFailed_Instance", "namespace": "AWS/EC2",
     "metric": "StatusCheckFailed_Instance", "stat": "Maximum", "unit": "", "chart": "value"},
    {"key": "network_in", "label": "NetworkIn", "namespace": "AWS/EC2",
     "metric": "NetworkIn", "stat": "Average", "unit": "bytes", "chart": "bar"},
    {"key": "network_packets_in", "label": "NetworkPacketsIn", "namespace": "AWS/EC2",
     "metric": "NetworkPacketsIn", "stat": "Average", "unit": "count", "chart": "bar"},
]

# Agent metrics (CWAgent namespace). Rely on aggregation_dimensions [["InstanceId"]]
# in the agent config so they can be queried with just the InstanceId dimension.
CWAGENT_METRICS = [
    {"key": "mem_free", "label": "Free Memory", "namespace": "CWAgent",
     "metric": "mem_available", "stat": "Average", "unit": "bytes", "chart": "pie"},
    {"key": "mem_used_pct", "label": "Memory Used %", "namespace": "CWAgent",
     "metric": "mem_used_percent", "stat": "Average", "unit": "%", "chart": "gauge"},
    {"key": "disk_used_pct", "label": "Root Disk Utilization", "namespace": "CWAgent",
     "metric": "disk_used_percent", "stat": "Average", "unit": "%", "chart": "bar"},
    {"key": "disk_busy", "label": "Disk Busy", "namespace": "CWAgent",
     "metric": "diskio_io_time", "stat": "Average", "unit": "ms", "chart": "bar"},
    {"key": "diskio_read", "label": "diskio_read_bytes", "namespace": "CWAgent",
     "metric": "diskio_read_bytes", "stat": "Average", "unit": "bytes", "chart": "bar"},
]

# EBS metrics, scoped to volumes attached to the in-scope EC2 instances.
EBS_METRICS = [
    {"key": "volume_queue", "label": "VolumeQueueLength", "namespace": "AWS/EBS",
     "metric": "VolumeQueueLength", "stat": "Average", "unit": "", "chart": "bar"},
    {"key": "burst_balance", "label": "BurstBalance", "namespace": "AWS/EBS",
     "metric": "BurstBalance", "stat": "Average", "unit": "%", "chart": "bar"},
]

# RDS metrics (account/region wide; admin-only by default — see RDS_* flags).
RDS_METRICS = [
    {"key": "rds_cpu", "label": "RDS CPU Utilization", "namespace": "AWS/RDS",
     "metric": "CPUUtilization", "stat": "Average", "unit": "%", "chart": "gauge"},
    {"key": "rds_connections", "label": "DatabaseConnections", "namespace": "AWS/RDS",
     "metric": "DatabaseConnections", "stat": "Average", "unit": "count", "chart": "value"},
    {"key": "rds_free_mem", "label": "RDS Free Memory", "namespace": "AWS/RDS",
     "metric": "FreeableMemory", "stat": "Average", "unit": "bytes", "chart": "value"},
]

# All per-instance metrics (EC2 native + agent), keyed for assembly.
INSTANCE_METRICS = EC2_METRICS + CWAGENT_METRICS
