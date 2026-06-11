/* CloudWatch health dashboard renderer.
 *
 * Fetches the RBAC-scoped snapshot from CWH_CONFIG.metricsUrl and renders:
 *   - per-instance CPU% / Memory% / status-check tiles (CSS gauges) for
 *     instances that actually have CloudWatch data
 *   - a compact "no data" summary for stopped / non-reporting instances
 *     (a stopped EC2 publishes NO metrics, native CPU included)
 *   - Highcharts column charts filtered to instances/volumes with data;
 *     charts with nothing to show are hidden entirely
 *   - Free Memory pie across reporting instances
 *   - RDS tiles (when present / permitted)
 *
 * Uses only core Highcharts chart types (column, pie) which ship with CloudBolt.
 */
(function () {
    "use strict";

    var cfg = window.CWH_CONFIG || {};

    function bytesToGB(v) { return v == null ? null : (v / (1024 * 1024 * 1024)); }
    function fmt(v, digits) {
        if (v == null) return "–";
        return Number(v).toFixed(digits == null ? 1 : digits);
    }
    function severityClass(pct) {
        if (pct == null) return "cwh-ok";
        if (pct >= 85) return "cwh-crit";
        if (pct >= 70) return "cwh-warn";
        return "cwh-ok";
    }
    function el(id) { return document.getElementById(id); }
    function isOff(inst) {
        return (inst.power_status || "").toUpperCase().indexOf("OFF") >= 0;
    }
    function hasData(inst) {
        var m = inst.metrics || {};
        return Object.keys(m).some(function (k) { return m[k] != null; });
    }

    function renderTiles(instances, data) {
        var root = el("cwh-tiles");
        root.innerHTML = "";
        if (!instances.length) {
            var why = "No AWS servers in scope.";
            if (data && data.errors && data.errors.length) {
                why = "Collection error: " + data.errors[0];
            } else if (data && data.skipped && Object.keys(data.skipped).length) {
                var bits = Object.keys(data.skipped).map(function (k) {
                    return k + " (" + data.skipped[k].length + ")";
                });
                why = "Servers skipped: " + bits.join(", ");
            }
            root.innerHTML = '<div class="col-xs-12 text-warning">' + why + '</div>';
            return;
        }

        var live = instances.filter(hasData);
        var dead = instances.filter(function (i) { return !hasData(i); });

        live.forEach(function (inst) {
            var m = inst.metrics || {};
            var cpu = m.cpu, mem = m.mem_used_pct;
            var failed = m.status_failed;
            var statusTxt = (failed == null) ? "–" : (failed >= 1 ? "FAILED" : "OK");
            var statusColor = (failed >= 1) ? "#d9534f" : "#5cb85c";
            var memHtml;
            if (mem == null) {
                memHtml =
                    '<div style="margin-top:6px;" class="text-muted"><small>Memory: no agent data</small></div>';
            } else {
                memHtml =
                    '<div style="margin-top:6px;"><span class="cwh-metric">' + fmt(mem) + '%</span> ' +
                       '<small class="text-muted">Mem used</small></div>' +
                    '<div class="cwh-bar"><span class="' + severityClass(mem) +
                       '" style="width:' + Math.min(mem, 100) + '%"></span></div>';
            }
            var html =
                '<div class="col-md-3 col-sm-6">' +
                  '<div class="cwh-tile">' +
                    '<h5 title="' + inst.hostname + '">' + inst.hostname +
                       ' <small>(' + inst.instance_id + ')</small></h5>' +
                    '<div><span class="cwh-metric">' + fmt(cpu) + '%</span> ' +
                       '<small class="text-muted">CPU</small></div>' +
                    '<div class="cwh-bar"><span class="' + severityClass(cpu) +
                       '" style="width:' + (cpu == null ? 0 : Math.min(cpu, 100)) + '%"></span></div>' +
                    memHtml +
                    '<div style="margin-top:6px;color:' + statusColor + ';font-weight:600;">' +
                       'Status: ' + statusTxt + '</div>' +
                  '</div>' +
                '</div>';
            root.insertAdjacentHTML("beforeend", html);
        });

        if (dead.length) {
            var items = dead.map(function (i) {
                var badge = isOff(i)
                    ? '<span class="label label-default">stopped</span>'
                    : '<span class="label label-warning">no data</span>';
                return '<span style="display:inline-block;margin:2px 10px 2px 0;white-space:nowrap;">' +
                       i.hostname + " " + badge + "</span>";
            });
            var stoppedCount = dead.filter(isOff).length;
            var headline = dead.length + " instance(s) with no CloudWatch data in the last hour";
            if (stoppedCount) {
                headline += " (" + stoppedCount + " powered off — stopped instances publish no metrics)";
            }
            root.insertAdjacentHTML("beforeend",
                '<div class="col-xs-12"><div class="cwh-tile" style="background:#fcfcfc;">' +
                  '<h5>' + headline + '</h5>' +
                  '<div style="line-height:22px;">' + items.join("") + '</div>' +
                '</div></div>');
        }
    }

    function column(containerId, title, categories, seriesData, opts) {
        opts = opts || {};
        var node = el(containerId);
        if (!node) return;
        var any = seriesData.some(function (s) {
            return (s.data || []).some(function (v) { return v != null; });
        });
        if (!categories.length || !any) { node.style.display = "none"; return; }
        node.style.display = "";
        if (typeof Highcharts === "undefined") return;
        Highcharts.chart(containerId, {
            chart: { type: "column" },
            title: { text: title, style: { fontSize: "13px" } },
            credits: { enabled: false },
            legend: { enabled: !!opts.legend },
            xAxis: { categories: categories, labels: { style: { fontSize: "10px" } } },
            yAxis: { title: { text: opts.yTitle || "" }, max: opts.max },
            tooltip: { valueDecimals: 2, valueSuffix: opts.suffix || "" },
            series: seriesData
        });
    }

    function pie(containerId, title, points) {
        var node = el(containerId);
        if (!node) return;
        if (!points.length) { node.style.display = "none"; return; }
        node.style.display = "";
        if (typeof Highcharts === "undefined") return;
        Highcharts.chart(containerId, {
            chart: { type: "pie" },
            title: { text: title, style: { fontSize: "13px" } },
            credits: { enabled: false },
            tooltip: { pointFormat: "<b>{point.y:.2f} GB</b> ({point.percentage:.1f}%)" },
            series: [{ name: "Free Memory (GB)", data: points }]
        });
    }

    /* Return {names, values} for one metric, restricted to instances that
       report it — keeps charts readable instead of rows of empty slots. */
    function seriesFor(instances, key) {
        var pts = instances.filter(function (i) { return (i.metrics || {})[key] != null; });
        return {
            names: pts.map(function (i) { return i.hostname || i.instance_id; }),
            values: pts.map(function (i) { return Number(i.metrics[key]); })
        };
    }

    function renderCharts(instances) {
        var s;

        s = seriesFor(instances, "disk_used_pct");
        column("cwh-disk-used", "Root Disk Utilization (%)", s.names,
            [{ name: "Disk used %", data: s.values, color: "#5b8def" }],
            { suffix: "%", max: 100 });

        var memPoints = instances.map(function (i) {
            return { name: i.hostname || i.instance_id, y: bytesToGB((i.metrics || {}).mem_free) };
        }).filter(function (p) { return p.y != null; });
        pie("cwh-free-mem", "Free Memory", memPoints);

        s = seriesFor(instances, "disk_busy");
        column("cwh-disk-busy", "Disk Busy (diskio_io_time)", s.names,
            [{ name: "io_time", data: s.values, color: "#f0ad4e" }]);

        s = seriesFor(instances, "diskio_read");
        column("cwh-diskio-read", "diskio_read_bytes", s.names,
            [{ name: "read bytes", data: s.values, color: "#5cb85c" }],
            { suffix: " B" });

        var net = instances.filter(function (i) {
            var m = i.metrics || {};
            return m.network_in != null || m.network_packets_in != null;
        });
        column("cwh-network", "NetworkIn / NetworkPacketsIn",
            net.map(function (i) { return i.hostname || i.instance_id; }), [
            { name: "NetworkIn (bytes)", color: "#5b8def",
              data: net.map(function (i) { var v = (i.metrics || {}).network_in; return v == null ? null : Number(v); }) },
            { name: "NetworkPacketsIn", color: "#d9534f",
              data: net.map(function (i) { var v = (i.metrics || {}).network_packets_in; return v == null ? null : Number(v); }) }
        ], { legend: true });

        s = seriesFor(instances, "status_failed");
        column("cwh-status-check", "StatusCheckFailed_Instance", s.names,
            [{ name: "Failed", data: s.values, color: "#d9534f" }],
            { max: 1 });

        // EBS — flatten volumes across instances, keep only volumes with data.
        var volNames = [], queue = [], burst = [];
        instances.forEach(function (i) {
            var vols = i.volumes || {};
            Object.keys(vols).forEach(function (volId) {
                var q = vols[volId].volume_queue, b = vols[volId].burst_balance;
                if (q == null && b == null) return;
                volNames.push(volId);
                queue.push(q == null ? null : Number(q));
                burst.push(b == null ? null : Number(b));
            });
        });
        column("cwh-volume-queue", "VolumeQueueLength", volNames,
            [{ name: "Queue length", data: queue, color: "#9b59b6" }]);
        column("cwh-burst-balance", "BurstBalance (%)", volNames,
            [{ name: "Burst balance", data: burst, color: "#1abc9c" }], { suffix: "%", max: 100 });
    }

    function renderRds(rds) {
        var section = el("cwh-rds-section");
        var root = el("cwh-rds-tiles");
        if (!rds || !rds.length) { section.style.display = "none"; return; }
        section.style.display = "block";
        root.innerHTML = "";
        rds.forEach(function (db) {
            var m = db.metrics || {};
            var html =
                '<div class="col-md-3 col-sm-6"><div class="cwh-tile">' +
                  '<h5 title="' + db.db_id + '">' + db.db_id + '</h5>' +
                  '<div><span class="cwh-metric">' + fmt(m.rds_cpu) + '%</span> <small class="text-muted">CPU</small></div>' +
                  '<div class="cwh-bar"><span class="' + severityClass(m.rds_cpu) +
                     '" style="width:' + (m.rds_cpu == null ? 0 : Math.min(m.rds_cpu, 100)) + '%"></span></div>' +
                  '<div style="margin-top:6px;">' + fmt(m.rds_connections, 0) + ' <small class="text-muted">connections</small></div>' +
                  '<div>' + fmt(bytesToGB(m.rds_free_mem)) + ' GB <small class="text-muted">free mem</small></div>' +
                '</div></div>';
            root.insertAdjacentHTML("beforeend", html);
        });
    }

    function setStatus(data) {
        var s = el("cwh-status");
        if (data.error) { s.innerHTML = '<span class="text-danger">' + data.error + '</span>'; return; }
        var instances = data.instances || [];
        var reporting = instances.filter(hasData).length;
        var when = data.generated ? new Date(data.generated).toLocaleString() : "now";
        var src = data.source === "cache" ? "cached" : "live";
        s.innerHTML = "Last " + data.window_minutes + " min · " + reporting + " of " +
                      instances.length + " instance(s) reporting · updated " + when + " (" + src + ")";
    }

    function load() {
        if (!cfg.metricsUrl) return;
        jQuery.getJSON(cfg.metricsUrl).done(function (data) {
            setStatus(data);
            if (data.error) return;
            var instances = data.instances || [];
            renderTiles(instances, data);
            renderCharts(instances.filter(hasData));
            renderRds(data.rds);
        }).fail(function (xhr) {
            el("cwh-status").innerHTML =
                '<span class="text-danger">Failed to load metrics (' + xhr.status + ').</span>';
        });
    }

    if (document.readyState !== "loading") { load(); }
    else { document.addEventListener("DOMContentLoaded", load); }
})();
