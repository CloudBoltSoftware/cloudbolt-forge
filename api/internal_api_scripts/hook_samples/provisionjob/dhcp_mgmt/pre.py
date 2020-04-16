import pre_networkdeconfig.py
from utilities.run_command import run_command as global_run_command


def run(job, logger):
    logger.info("in %s job.id=%s" % (__name__, job.id))

    # try:
    servers_list = job.job_parameters.cast().servers.all()
    for server in servers_list:
        # run disable_network_services for each server in job
        logger.info("working on server: %s" % server)
        pre_networkdeconfig.disable_network_services(server, logger)
    # except:
    #    return "FAILURE", "aborting job based on hook error", "failed on running custom job hook"

    return "", "", ""
