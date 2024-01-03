"""
Template for a CloudBolt Plugin that allows for local execution. 
To run this locally from the CloudBolt server, run the following command:
python plugin_template.py <job_id>
"""

# This section allows for the loading of the Django CloudBolt environment if
# this script is being run locally.
if __name__ == '__main__':
    import os
    import sys
    import django
    sys.path.extend(['/opt/cloudbolt', '/var/opt/cloudbolt/proserv'])
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
    django.setup()

from common.methods import set_progress
from jobs.models import Job
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job=None, *args, **kwargs):
    server = job.server_set.first()
    # Set Progress shows the log output in the job details page
    set_progress('Running this command on server {}'.format(server))
    # Loggers are used to write to the CloudBolt log file
    logger.info('Running this command on server {}'.format(server))
    return "", "", ""


# This section allows for the loading of the Django CloudBolt environment if
# this script is being run locally. Running the script locally takes in one
# argument, the job id. This could be extended to take in additional args.
if __name__ == '__main__':
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    run = run(job)
    if run[0] == 'FAILURE':
        set_progress(run[1])
