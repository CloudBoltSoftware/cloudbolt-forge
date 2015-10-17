"""
Sample CloudBolt plug-in for a 'service action' that asks the user for a
parameter value and adds that parameter value to every server in this deployed
service.

Set the PARAM_NAME constant below to the name of the desired parameter.

To enable:
    Go to Admin > Service Actions
    Click "New Service Action" > CloudBolt Plug-in > "Add new cloudbolt plugin"
    Fill out the form and upload this Python script.

When uploading this script, CB recognizes the 'param_value' below as an "Action
Input" (due to the double curly braces) and lets you set additional properties
on this such as a label, description, type, and constraints on its value.
You may want to set the label of that action input to match the label of the
parameter being set, but it's up to you.
"""

from common.methods import set_progress, create_decom_job_for_servers
from jobs.models import Job


# This is the parameter whose value will be set on all servers.  You can enable
# its "Show on servers" property to confirm that this action works as intended.
PARAM_NAME = 'monitoring_plan'


def run(job, **kwargs):
    # User enters this value in the service action dialog.
    param_value = '{{ param_value }}'

    logger = kwargs['logger']  # use this to send text to the job log file
    job_params = job.job_parameters.cast()
    service = job_params.services.first()

    set_progress('Setting parameter "{}" = "{}" on all severs in service {}'
                 .format(PARAM_NAME, param_value, service))

    # Get all servers
    # servers = service.server_set.all()
    # --- or ---
    # Get only non-historical servers, in case any were deleted (they remain in
    # the CB database and associated to this service)
    servers = service.server_set.exclude(status='HISTORICAL')

    # Set the param on each server
    for server in servers:
        server.set_value_for_custom_field(PARAM_NAME, param_value)
        set_progress('  Server "{}"'.format(server))

    return '', '', ''
