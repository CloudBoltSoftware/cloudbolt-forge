import time

"""
Sample hook for showing how arbitrary actions can be triggered when parameters
change.

To use, create a boolean parameter existing with the name "enable_backups",
set "Show on servers" to true, associate it with an environment, and upload
this hook and attach it to that parameter. Then change the value of the
parameter on a server - this code will run to take the appropriate action.
"""


def run(job, logger=None):
    params = job.job_parameters.cast()
    server = params.instance
    enable_backups = params.post_custom_field_value.value
    # original_value = params.pre_custom_field_value.value

    if enable_backups:
        msg1 = "Contacting Veam to enable backups on server {}".format(server.hostname)
        msg2 = "Backups have been enabled"
    else:
        msg1 = "Contacting Veam to disable backups on server {}".format(server.hostname)
        msg2 = "Backups have been disabled"
    job.set_progress(msg1)
    time.sleep(2)
    # useful for testing auto-rollback of the parameter value:
    # return "FAILURE", "Intentional failure, CloudBolt will reset the parameter value to {}".format(original_value), ""
    job.set_progress(msg2)
    time.sleep(2)
    job.set_progress("Veam returned status: Successful!")
    return "", "", ""
