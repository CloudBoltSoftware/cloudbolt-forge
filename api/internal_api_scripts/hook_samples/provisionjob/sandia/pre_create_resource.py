from hpoo_handler import run_hpoo_flow, launch_hpoo_flow


def run(job, lock):
    print "in %s job.id=%s" % (__name__, job.id)
    server = job.server_set.all()[0]
    server_info = "Server info: CPUs: %s, Mem: %s, IP: %s, Hostname: %s" % (
        server.cpu_cnt, server.mem_size, server.ip, server.hostname)
    oo_params = {'server_info': server_info}
    job.set_progress("Now calling orchestration to register server with NWIS")
    oo_url, oo_response, soup_response, dict_response, flow_results = launch_hpoo_flow(
        '134.253.232.101', 'fe1859df-68fe-43b0-b92c-a1e24b95107d', oo_params, 'admin', 'up=tiVr7', oo_port="8443", oo_sync="execute")
    nwis_output = flow_results['nwis_output']

    job.set_progress("Done calling orchestration to register server with NWIS, results=%s" %
                     (nwis_output))
    # return "FAILURE", "aborting job based on pre_application hook error",
    # "failed on server network connection step"

    return "", "", ""
