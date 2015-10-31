import time

from jobs.models import Job

TIMEOUT = 600


def is_reachable(server):
    instance_id = server.ec2serverinfo.instance_id
    ec2_region = server.ec2serverinfo.ec2_region

    rh = server.resource_handler.cast()
    rh.connect_ec2(ec2_region)
    wc = rh.resource_technology.work_class

    instance = wc.get_instance(instance_id)
    status = instance.connection.get_all_instance_status(instance_id)
    return True if status[0].instance_status.details[u'reachability'] == u'passed' else False


def run(job, logger=None, **kwargs):
    assert isinstance(job, Job) and job.type == u'provision'

    server = job.server_set.first()
    timeout = time.time() + TIMEOUT

    while True:
        if is_reachable(server):
            job.set_progress("EC2 instance is reachable.")
            break
        elif time.time() > timeout:
            job.set_progress("Waited {} seconds. Continuing...".format(TIMEOUT))
            break
        else:
            time.sleep(2)

    return "", "", ""
