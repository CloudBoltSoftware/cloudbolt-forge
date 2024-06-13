"""
This hook will stall, adding to the progress of the job, until it detects the
existence of a file /var/tmp/stop

Useful for pausing a job, or testing the job engine's hook execution
"""
import logging
import time
import os

logger = logging.getLogger(__name__)


def run(job, logger=None):
    while not os.path.isfile("/var/tmp/stop"):
        job.set_progress(
            "in the hook for job {}. job.status={}. touch "
            "/var/tmp/stop to stop this hook".format(job.id, job.status)
        )
        time.sleep(30)
    job.set_progress("Found /var/tmp/stop, exiting hook")
    return "", "", ""
