from hpoo_handler import run_hpoo_flow, launch_hpoo_flow


def run(job, lock):
    print "in %s job.id=%s" % (__name__, job.id)
    server = job.server_set.all()[0]
    if not server.enable_monitoring:
        job.set_progress("NOTICE: Monitoring was not selected.")
        return "", "", ""

    #server_info = "Server info: CPUs: %s, Mem: %s, IP: %s, Hostname: %s" % (server.cpu_cnt, server.mem_size, server.ip, server.hostname)
    oo_params = {
        'hostname': server.hostname, 'IPAddress': server.ip, 'OSType': server.os_family.name,
        'reqUserName': server.owner.user.username, 'reqOrgName': server.group.name}
    job.set_progress("Now calling orchestration to activate SiteScope monitors")
    oo_url, oo_response, soup_response, dict_response, flow_results = launch_hpoo_flow(
        '134.253.232.101', '867efbf8-b9fa-40bd-b2bf-a952819617da', oo_params, 'admin', 'up=tiVr7', oo_port="8443", oo_sync="execute")
    flowResult = flow_results['flowResult']

    job.set_progress("Done calling orchestration to activate SiteScope monitors, results=%s" %
                     (flowResult))
    # return "FAILURE", "aborting job based on pre_application hook error",
    # "failed on server network connection step"

    return "", "", ""
