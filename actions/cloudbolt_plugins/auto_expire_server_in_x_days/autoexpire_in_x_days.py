import sys
import datetime

from common.methods import set_progress

from jobs.models import Job


def run(job, logger=None):
    """
    Attach this plug-in to the Post-Provision trigger to automatically set
    set the expiration date for each server in the given job
    to X day(s) from today. Note: Since expiration happens at 00:00 on the
    date specified, the server will remain online until the next
    expiration job run.

    :param job: Job
    """
    one_day = datetime.datetime.now() + datetime.timedelta(days=int('{{ number_of_days }}'))
    date_string = "{:%m/%d/%Y}".format(one_day)
    job.set_progress("Setting expiration date for servers in this job to: {}".format(date_string))

    for server in job.server_set.all():
        server.set_value_for_custom_field("expiration_date", date_string)

    return "", "", ""


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <Job ID>\n" % sys.argv[0])
        sys.exit(2)

    job_id = sys.argv[1]
    run(Job.objects.get(id=job_id))
