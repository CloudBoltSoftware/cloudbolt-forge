"""
Server Action to extend the expiration date of a Server by 30 days and notify
Approvers in the Server's Group.
"""

import datetime

from utilities.logger import ThreadLogger
from utilities.mail import send_mail, InvalidConfigurationException

logger = ThreadLogger(__name__)


def run(job, logger=None):
    # Extend Server Expiration Date
    server = job.server_set.first()

    # If the server doesn't have an expiration date, this Server Action will
    # quit and _not_ assign it one.
    if server.expiration_date is None:
        return "", "This server does not have an expiration date.", ""

    new_date = server.expiration_date + datetime.timedelta(days=30)
    server.set_value_for_custom_field("expiration_date", new_date)

    # Notify Approvers
    email_body = (
        f"{job.owner} has extended {server.hostname}'s expiration date by 30 days."
    )
    email_addrs = [approver.user.email for approver in server.group.get_approvers()]
    subject = "CloudBolt: Server expiration extended by 30 days."
    try:
        send_mail(subject, email_body, None, email_addrs)
    except InvalidConfigurationException:
        logger.debug("Cannot connect to email (SMTP) server")
    return "", "", ""
