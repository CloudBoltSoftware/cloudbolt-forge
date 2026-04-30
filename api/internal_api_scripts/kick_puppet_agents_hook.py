"""
An orchestration hook meant for the 'Waiting for Config Manager Agent Checkin'
hook point. It (pretends to) kick a Puppet run on all of the Job's associated
servers, thereby speeding up the time for app installations to complete.
"""
import time

from connectors.puppet.models import PuppetNode


def run(job, logger=None):
    cb_server_records = job.server_set.all()
    puppet_node_names = []

    for server in cb_server_records:
        try:
            certname = server.puppet_node.certname
        except PuppetNode.DoesNotExist:
            no_kick_reason = "no corresponding Puppet node was found"
        else:
            puppet_node_names.append(certname)
            continue

        try:
            certname = ".".join(
                [server.hostname, server.nics.first().network.dns_domain]
            )
        except Exception as e:
            no_kick_reason = "a certname could not be guessed (Exception: {})".format(e)
        else:
            job.set_progress(
                "Could not find a Puppet node for server {}, guessing the "
                "certname is {}".format(server, certname)
            )
            puppet_node_names.append(certname)
            continue

        job.set_progress(
            "Not kicking a Puppet run for server {} because {}".format(
                server, no_kick_reason
            )
        )

    for certname in puppet_node_names:
        job.set_progress(
            'Pretending to kick off a Puppet run for "{}"'.format(certname)
        )
        kick(certname)

    job.set_progress("Done kicking Puppet runs.")

    return "", "", ""


def kick(certname):
    """
    (Prentend to) kick off a Puppet run for the Puppet agent having
    certname `certname`.
    """
    time.sleep(10)
