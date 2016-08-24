"""
THEN Rule Action

Locate sync jobs older than the provided amount of days
and removes the associated log files from the filesystem
"""

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import sys
sys.path.append('/opt/cloudbolt')
from common.methods import set_progress
from utilities.logger import ThreadLogger
logger = ThreadLogger(__name__)
from jobs.models import Job
from common.methods import set_progress
from django.conf import settings

def run(job, logger, *args, **kwargs):
    params = job.job_parameters.cast().arguments
    jobs = params['sync_jobs']
    sync_jobs = Job.objects.filter(id__in=jobs)
    set_progress("Rule will delete {} jobs".format(sync_jobs.count()))
    for job in sync_jobs:
        logfile = os.path.join(settings.VARDIR, "log", "cloudbolt", "jobs", "{}{}".format(str(job.id), ".log"))
        if os.path.exists(logfile):
            set_progress("Removing log file {}".format(logfile))
            os.remove(logfile)
    sync_jobs.delete()
    return ("SUCCESS", "", "")

if __name__ == "__main__":
    print run(job=Job.objects.get(id=sys.argv[1]), logger=None)
