import datetime
from infrastructure.models import Server

"""
Hook used at the post syncvms hook point to set expiration date on newly synced
servers.

Finds all servers that do not yet have the expiration_date custom field set,
then sets it to the given number of days from the current day.

Make sure that the action has a default value set for Days Before Expire.

Remove the hour, minute, second, and microsecond from the datetime object
because our current datepicker widget does not handle these values.
"""


def run(job, logger=None):
    expiry_days = int('{{days_before_expire}}')
    jp = job.job_parameters.cast()
    job.set_progress(
        "Setting expiration date on newly discovered servers "
        "to {} days from now".format(expiry_days)
    )
    # get all servers for Resource Handlers being sync'ed
    servers = Server.objects.filter(resource_handler__in=jp.resource_handlers.all())
    # no need to set date on deleted servers
    servers = servers.exclude(status="HISTORICAL")
    counter = 0
    expiration_time = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    expiration_time = expiration_time.replace(hour=0, minute=0, second=0, microsecond=0)
    for s in servers:
        if not s.get_value_for_custom_field("expiration_date"):
            # expiration date is not set, so we set it to X days from now
            s.expiration_date = expiration_time
            s.save()
            counter += 1
    job.set_progress("Set expiration date on {} servers".format(counter))
    return "", "", ""
