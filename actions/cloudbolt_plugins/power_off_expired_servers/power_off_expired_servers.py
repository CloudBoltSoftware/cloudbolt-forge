from utilities import events


def run(job, logger=None, **kwargs):
    """
    A post-expire hook that, given a list of expired servers, powers off any that are not off yet.

    The expiration_date parameter is used to determine whether a server is expired.

    Also updates their history with the event & an explanation.
    """
    for server in job.server_set.all():
        if server.power_status != "POWEROFF":
            job.set_progress("Powering off %s." % server.hostname)
            server.power_off()
            msg = "Server powered off because it expired at %s." % (server.expiration_date)
            events.add_server_event('MODIFICATION', server, msg, job=job)
    return '', '', ''
