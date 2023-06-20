from cbhooks.models import ServerAction


def run(job, *args, logger=None, **kwargs):
    # Replace the label of the remote script in the next line with whatever remote script you want to run (can also look it up by id)
    action = ServerAction.objects.get(label="Patch Linux Server")
    servers = kwargs.pop("servers", None)
    if not servers or len(servers) == 1:
        server = kwargs.pop("server", None)
        if not server:
            return "FAILURE", "", "No 'server' or 'servers' argument found"
        # There's just one server, so no point in spawning a sub-job
        return action.run_hook(owner=job.owner, server=server, parent_job=job, **kwargs)
        
    jobs = []
    for server in servers:
        subjob = action.run_hook_as_job(owner=job.owner, server=server, parent_job=job, **kwargs)
        jobs.append(subjob)
    job.wait_for_sub_jobs()
    
    return "SUCCESS", f"Completed {len(jobs)} sub-jobs", ""