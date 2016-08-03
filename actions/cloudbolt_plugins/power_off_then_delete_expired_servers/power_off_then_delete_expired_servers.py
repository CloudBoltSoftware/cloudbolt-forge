#!/usr/local/bin/python
"""
Post-expire CloudBolt Plug-in that sends warning emails and possibly powers off
or deletes a server depending on how expired it is.

Parameters include the number of days a server should be expired before it is
powered off and the number of days it should be expired before it is deleted.
The hook also needs the hostname of a CB instance to use when providing links in
the warning emails.
"""


import sys
import datetime

from common.methods import create_decom_job_for_servers
from jobs.models import Job
from utilities.logger import ThreadLogger
from utilities.mail import send_mail
from utilities.mail import InvalidConfigurationException

logger = ThreadLogger(__name__)

CB_HOSTNAME = '{{cb_hostname}}'

POWEROFF_AFTER_DAYS = {{days_before_poweroff}}
DELETE_AFTER_DAYS = {{days_before_delete}}


def run(job, *args, **kwargs):
    expired_servers = job.job_parameters.cast().servers.all()

    for server in expired_servers:
        job.set_progress('Now working on server {}'.format(server.hostname))
        if server.status == 'HISTORICAL':
            job.set_progress(' Server is historical')
            continue

        days_expired = get_days_expired(server)
        job.set_progress(' Server expired {} days ago'.format(days_expired))
        if days_expired >= DELETE_AFTER_DAYS:
            job.set_progress(' Deleting server...')
            delete_server_and_send_email(server, job)
        elif days_expired >= POWEROFF_AFTER_DAYS:
            job.set_progress(' Powering off server...')
            power_off_and_send_email(server, days_expired, job)
        else:
            job.set_progress(' Sending warning email...')
            warn_and_send_email(server, days_expired)

    return "", "", ""


def get_days_expired(server):
    """
    Determines the number of days by which the server is expired, for use in
    the logic of deciding what action to take
    """
    exp_date = server.get_value_for_custom_field('expiration_date')
    today = datetime.datetime.now()
    days_expired = (today - exp_date).days
    return days_expired


def warn_and_send_email(server, days_expired):
    """
    If the server is expired but not sufficiently so to merit powering off or
    deleting, simply send a warning email
    """
    email_body = (
        'This is an email reminder that your server "{}" '
        'has expired and will be powered off in {} days '
        'if no further action is taken. If this is undesired, '
        'please log into {}/servers/{}/#tab-parameters '
        'and change the expiration date.'.format(
            server.hostname,
            POWEROFF_AFTER_DAYS - days_expired,
            CB_HOSTNAME,
            server.id)
    )
    email_owner(email_body, server)


def delete_server_and_send_email(server, job):
    """
    If the server is old enough, delete it and send an email to inform the owner
    """
    create_decom_job_for_servers([server], parent_job=job)

    email_body = (
        'This is an email notifying you that your server "{}" '
        'has been deleted. Please contact your CloudBolt administrator '
        'for more information.'.format(
            server.hostname)
    )
    email_owner(email_body, server)


def power_off_and_send_email(server, days_expired, job):
    """
    If the server is expired a number of days between the cutoff for powering
    off and the cutoff for deletion, power it off and send a notification/
    warning email to the owner
    """
    powered_off = server.power_off()
    if not powered_off:
        job.set_progress(' Server power off failed, see logs')

    email_body = (
        'This is an email reminder that your server "{}" '
        'has expired and will now be powered off. '
        'If further action is not taken, the server will '
        'be deleted in {} days. Go to '
        '{}/servers/{}/#tab-parameters to change the '
        'server expiration date.'.format(
            server.hostname,
            DELETE_AFTER_DAYS - days_expired,
            CB_HOSTNAME,
            server.id)
    )
    email_owner(email_body, server)


def email_owner(body, server):
    """
    Send an email to the server's owner with the given contents
    """
    logger.info('Sending email with contents: {}'.format(body))
    owner = server.owner
    if not owner:
        logger.debug('Server has no owner, will not send email')
        return

    email = server.owner.user.email
    subject = 'CloudBolt: Server expiration warning!'
    try:
        send_mail(subject, body, None, [email])
    except InvalidConfigurationException:
        logger.debug('Cannot connect to email (SMTP) server')


#if __name__ == '__main__':
#    job = Job.objects.get(id=sys.argv[1])
#    print run(job)
