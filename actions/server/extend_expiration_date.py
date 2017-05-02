import datetime
from utilities.logger import ThreadLogger
from utilities.mail import send_mail
from utilities.mail import InvalidConfigurationException

"""
Server action to extend expiration date on a server by 30 days
"""

def run(job, logger=None):
    # Extend Server Expiration Date
    server = job.server_set.first()
    new_date = server.expiration_date + datetime.timedelta(days=30)
    server.set_value_for_custom_field("expiration_date", new_date)
    
    # Notify Approver
    email_body = (
        '{} has extended {}\'s expiration date by 30 days.'.format(job.owner, server.hostname)
    )
    emails = []
    for approver in server.group.approvers.all():
        emails.append(approver.user.email)
    subject = 'CloudBolt: Server expiration extended by 30 days.'
    try:
        send_mail(subject, email_body, None, emails)
    except InvalidConfigurationException:
        logger.debug('Cannot connect to email (SMTP) server')
    return "", "", ""
