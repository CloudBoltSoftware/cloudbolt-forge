import datetime
from infrastructure.models import Server


def run(job, logger=None):
    jp = job.job_parameters.cast()
    job.set_progress("Setting exiration date on newly discovered servers")
    # get all servers for RHs being sync'ed
    servers = Server.objects.filter(resource_handler__in=jp.resource_handlers.all())
    # no need to set date on delete servers
    servers = servers.exclude(status="HISTORICAL")
    counter = 0
    six_months = datetime.datetime.now() + datetime.timedelta(180)
    six_months = six_months.replace(hour=0, minute=0, second=0, microsecond=0)
    for s in servers:
        if not s.get_value_for_custom_field("expiration_date"):
            # expiration date is not set, so we set it to 180 days from now
            s.expiration_date = six_months
            s.save()
            counter += 1
    job.set_progress("Set expiration date on {} servers".format(counter))
    return "", "", ""
