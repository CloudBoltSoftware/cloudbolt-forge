from jobs.models import Job

def run(job, logger=None, **kwargs):
    parameters = job.job_parameters.cast()
    servers = parameters.servers.all()
    # Check if the job was empty, just in case
    if not servers:
        return "WARNING", "", "No server in job"
    # Add the Expired tag
    for server in servers:
        server.tags.add("Expired")

    return "", "", ""
