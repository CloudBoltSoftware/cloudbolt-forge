"""
Requires parameter 'User Manager' for a user profile CFV
"""
from utilities.mail import email


class FakeRequest(object):
    def __init__(self, domain):
        self.META = {'HTTP_HOST': domain}


def run(order, job=None, **kwargs):
    profile = order.owner
    manager = profile.user_manager
    approver_email = manager.email
    fake_request = FakeRequest("my.domain.com")
    email(slug='order-created',
          recipients=approver_email,
          context={'order': order, 'request': fake_request})
    return "SUCCESS", "", ""
