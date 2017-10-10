#!/usr/bin/env python

""" cb-hook_bigip-add-or-remove-from-pool.py
Cloudbolt plugin intended to be used in the following orchestration points:
    'Delete Server' Orchestration Hook: 'Pre-Delete' action
    'Provision Server' Orchestration Hook: 'Post Provision' action



TODO:   on add to pool, if using parameter, add server to service

"""
import sys
import re
import ast
import traceback

from nuance_big_ip_f5_ltm import nuance_big_ip_f5_ltm as n_f5
from c2_wrapper import (create_custom_field_value,
                        attach_custom_field_option,
                        attach_custom_field)
from services.models import Service


cb_param_pool          = "big_ip_f5_ltm_pool_name"
cb_param_pool_port     = "big_ip_f5_ltm_pool_port"
cb_param_pool_portlist = "big_ip_f5_ltm_pool_ports"


def run(job=False, logger=None):
    if job:
        try:
            servers = job.job_parameters.cast().servers.all()
        except:
            servers = job.server_set.all()

        try:
            server_count = job.job_parameters.cast().servers.count()
        except:
            server_count = job.server_set.count()

        debug("Servers (%s): %s" % (server_count, servers), logger)

        if job.type == "decom":
            bigip_job_type = "DEL"
        elif job.type == "provision":
            bigip_job_type = "ADD"
            param_value = getattr(servers[0], cb_param_pool, None)
        elif job.type == "orchestration_hook":
            param_value = getattr(servers[0], cb_param_pool, None)
            if (param_value is not None and len(param_value) > 8):
                bigip_job_type = "DEL"
            else:
                bigip_job_type = "ADD"
        else:
            return ("WARNING", "Unexpected Job type", "CB JOB: %s" % job.type)
        debug("BigIP/F5 Job Type: '%s'" % bigip_job_type, logger)

        if server_count == 0:
            return("FAILURE",
                   "No server references were associated with this job.",
                   "Server Count: %i" % server_count)
    else:
        servers = [Server.objects.get(id=serverId)]

    for server in servers:
        joblog("processing Server: '%s',"
               "Id: '%s',"
               "IP: '%s'" % (server, server.id, server.ip), job)
        try:
            service = Service.objects.get(id=server.service.id)
            debug("server is assigned to service: '%s'" % service.name, logger)
        except Exception as e:
            debug("Exception caught:  %s" % e.message, logger)
            debug("server is not assigned to a service", logger)
            service = False
        if bigip_job_type == "DEL":
            msg = remove_from_pool(job, server, service, logger)
        elif bigip_job_type == "ADD":
            if (not service and param_value is not None
                    and len(getattr(server, cb_param_pool, None)) > 8):
                service_id = getattr(server, cb_param_pool, None)
                service_id = service_id.split('_')[0].split('-')[-1]
                try:
                    int(service_id)
                except:
                    return ("WARNING",
                            "'%s' is not an integer" % (service_id),
                            "Look at server param: '%s'" % (cb_param_pool))
                service = join_service(job, server, service_id)
            msg = add_to_pool(job, server, service, logger)
        else:
            return ("FAILURE", "BIGIP task type unknown", "ADD|DEL not found")
    return ("", msg, "")


def add_to_pool(job, server, service, logger):
    f5_handle = n_f5.connect(server.big_ip_f5_ltm_ip,
                             server.big_ip_f5_ltm_username,
                             server.big_ip_f5_ltm_password)
    try:
        # In the past, a job that deployed a blueprint had a type of install_service.
        # Starting in 7.5, its type will be deploy_blueprint
        if (not service and job.parent_job
                and (job.parent_job.type == 'install_service'
                    or job.parent_job.type == 'deploy_blueprint')):
            debug("trying one more time to set service", logger)
            service = Service.objects.last()
        debug("Service: '%s', ID: '%s'" % (service.name, service.id), logger)
        f5_pool_base = "%s-%i_" % (service.name, service.id)
        f5_pool_base = re.sub('[^0-9a-zA-Z_]+', '-', f5_pool_base)
    except AttributeError:
        f5_pool_base = ""
    applications = server.applications.all()
    apps_to_pool = getattr(server, cb_param_pool_portlist, None)
    apps_to_pool = ast.literal_eval(apps_to_pool).keys()
    debug("Target Applications: %s" % apps_to_pool, logger)
    param_dict = {}
    for app in applications:
        if app.name in apps_to_pool:
            f5_type = app.name.split()[0].lower()
            f5_pool_name = "/Common/%s%s-pool" % (f5_pool_base, f5_type)
            f5_pool_ports = getattr(server, cb_param_pool_portlist, None)
            f5_pool_ports = ast.literal_eval(f5_pool_ports)
            f5_pool_port = f5_pool_ports[app.name]
            param_dict[cb_param_pool] = f5_pool_name
            param_dict[cb_param_pool_port] = f5_pool_port
            msg = n_f5.createPoolIfNotExistsAndAddMember(server.ip,
                                                         str(f5_pool_port),
                                                         f5_pool_name,
                                                         f5_handle)
            if isinstance(msg, tuple):
                status, stdout, stderr = str(msg[0]), str(msg[1]), str(msg[2])
                joblog(stdout, job)
                debug("Status: %s\t ErrOut: %s" % (status, stderr), logger)
            else:
                joblog("return value '%s' was not a tuple" % msg, job)
            set_parameter(logger, server, param_dict, on_server=True)
        else:
            return("[%s] No applications are assigned to this host." % server)
    return("[%s] Processed all Applications" % server)


def remove_from_pool(job, server, service, logger):
    f5_handle = n_f5.connect(server.big_ip_f5_ltm_ip,
                             server.big_ip_f5_ltm_username,
                             server.big_ip_f5_ltm_password)
    f5_pool_name = getattr(server, cb_param_pool, None)
    f5_pool_port = getattr(server, cb_param_pool_port, None)
    msg = n_f5.removeMemberFromPool(server.ip,
                                    str(f5_pool_port),
                                    f5_pool_name,
                                    f5_handle)
    if isinstance(msg, tuple):
        status, stdout, stderr = str(msg[0]), str(msg[1]), str(msg[2])
        joblog(stdout, job)
        debug("Status: %s\t ErrOut: %s" % (status, stderr), logger)
    else:
        joblog("return value '%s' was not a tuple" % msg, job)
    setattr(server, cb_param_pool, "")
    setattr(server, cb_param_pool_port, None)
    debug("[%s] Removed '%s' and '%s' parameters"
          % (server, cb_param_pool, cb_param_pool_port), logger)
    return("[%s] Processed all Applications" % server)


def set_parameter(logger, server, param_dict={}, on_server=False):
    for k in param_dict.keys():
        try:
            cfv = create_custom_field_value(custom_field_name=k,
                                            value=param_dict[k])
        except Exception, e:
            debug("Creating parameter Value: %s failed: %s - %s"
                  % (param_dict[k], e, traceback.format_exc()), logger)

        try:
            attach_custom_field_option(object=server.environment,
                                       custom_field_option=cfv)
            debug("'%s' added to Parameter: '%s' in Environment: '%s'"
                  % (param_dict[k], k, server.environment), logger)
        except Exception, e:
            debug("Creating Parameter Option: %s failed: %s - %s"
                  % (cfv, e, traceback.format_exc()))

        try:
            attach_custom_field(object=server.environment,
                                custom_field_name=k)
            debug("Added parameter: '%s' to Environment: '%s'"
                  % (k, server.environment), logger)
        except Exception, e:
            debug("Creating parameter: '%s' failed: %s - %s"
                  % (k, e, traceback.format_exc()))
        if on_server:
            setattr(server, k, param_dict[k])
            debug("'%s':'%s' add to %s" % (k, param_dict[k], server), logger)


def join_service(job, server, service_id):
    service = Service.objects.filter(id=service_id)[0]
    server.service = service
    server.save()
    joblog("Added: '%s' to Service: '%s'" % (server, server.service), job)
    return service


def debug(message, logger):
    if logger:
        logger.debug(message)
    else:
        print message


def joblog(message, job):
    if job:
        job.set_progress(message)
    else:
        print message


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("usage: %s [ADD|DEL] <Cloudbolt server id>\n" %
                         sys.argv[0])
        sys.exit(2)
    if sys.argv[1] not in ['ADD', 'DEL']:
        sys.stderr.write("Error: '%s' must supply 'ADD' or 'DEL'\n" %
                         sys.argv[1])
        sys.exit(2)
    try:
        isinstance(int(sys.argv[2]), int)
    except:
        sys.stderr.write("Error: '%s' must be an integer\n" % sys.argv[1])
        sys.exit(2)
    sys.path.insert(0, "/opt/cloudbolt")

    from c2_wrapper import Server

    bigip_job_type = sys.argv[1]
    serverId = sys.argv[2]

    run()
