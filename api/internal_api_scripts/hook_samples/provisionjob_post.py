"""For each successful job, if a custom field 'enable_monitoring' is set,
send an email to the CB admin.

For this hook to work, you need to create a new parameter in the Admin
UI called 'enable_monitoring', and attach it to a group or environment.
Then when provisioning a server, a check box for this option will appear
in the new order item dialog. This box must be checked for the hook to
send the email.

Then set ENABLE_MONITORING_EMAIL in customer_settings.py to the email address
that should be notified of new servers that should have monitoring enabled and
add two files to /var/opt/cloudbolt/proserv/templates/email:
enable-monitoring-subj.template and enable-monitoring-body.template.
"""
from django.conf import settings
from django.template.loader import render_to_string

from utilities import mail
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, logger=None):
    if job.status != "SUCCESS":
        return "", "", ""

    server = job.server_set.first()
    enable_monitoring = server.enable_monitoring

    if enable_monitoring:
        job.set_progress("Enable monitoring is set for this job.")

        if hasattr(settings, "ENABLE_MONITORING_EMAIL"):
            email_context = {"owner": job.owner, "server": server}
            recipient = getattr(settings, "ENABLE_MONITORING_EMAIL")

            try:
                mail.email([recipient], "enable-monitoring", context=email_context)
            except Exception as err:
                return "FAILURE", "Aborting due to email error. ", str(err)
            # mail utility already logs this, so just update job progress
            job.set_progress("Email sent to %s" % recipient)
        else:
            job.set_progress(
                "Email not sent because customer_settings.ENABLE_MONITORING_EMAIL is not set.",
                logger=logger,
            )
    else:
        job.set_progress("Monitoring not enabled.")

    return "", "", ""
