from jobs.models import Job


def run(job, logger, **kwargs):
    """
    Given a list of expired servers, create decommission jobs for all servers.
    Servers will be grouped by environment.
    """

    # this import done here to avoid circular dependencies
    from orders.models import DecomServerOrderItem

    # group servers by environment
    env_servers = {}
    for server in job.server_set.all():
        env = server.environment
        if env.name in env_servers:
            env_servers[env.name]["servers"].append(server)
        else:
            env_servers[env.name] = {"environment": env, "servers": [server]}

    for val in env_servers.values():
        oi = DecomServerOrderItem(
            order=None, environment=val["environment"], pre_decom=False
        )
        oi.save()
        oi.servers.set(val["servers"])
        decom_job = Job(type="decom", job_parameters=oi, owner=None)
        decom_job.parent_job = job
        decom_job.save()

    return "", "", ""
