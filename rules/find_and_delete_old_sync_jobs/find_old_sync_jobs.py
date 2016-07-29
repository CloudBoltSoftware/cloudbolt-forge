"""
IF Rule Action

Locate sync jobs older than the provided amount of days
"""

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import sys
import datetime
import json
sys.path.append('/opt/cloudbolt')
from common.methods import set_progress
from utilities.logger import ThreadLogger
logger = ThreadLogger(__name__)
from jobs.models import Job

days = '{{ threshold_days_before_delete }}'

def check(job, logger, days=days, *args, **kwargs):
    delete_date = datetime.datetime.now() - datetime.timedelta(days=int(days))
    sync_jobs_total = Job.objects.filter(type="syncvms").count()
    set_progress("Total sync jobs {}".format(sync_jobs_total))
    sync_jobs = Job.objects.filter(type="syncvms", start_date__lt=delete_date).exclude(status="RUNNING")
    set_progress("Found {} jobs to delete".format(sync_jobs.count()))
    sync_jobs_ids = list(sync_jobs.values_list('id', flat=True))
    return ("SUCCESS", "", "", {'sync_jobs': sync_jobs_ids})

if __name__ == '__main__':
    days_arg = sys.argv[1]
    check(days=days_arg, job=None)
