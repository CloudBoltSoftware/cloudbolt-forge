"""
Multiple Group Approval
~~~~~~~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires users from two separate Groups approve an Order before it
becomes Active.


Configuration
~~~~~~~~~~~~~
If the user that submitted this Order belongs to "Workers", this plugin
requires one of two scenarios:
    1) "Finance" and "IT" groups both have "Approval Permission" for "Workers";
    2) The approving users are Approvers in both Groups (i.e. "Finance" and
       "IT").


Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""

from accounts.models import Group


def run(order, *args, **kwargs):
    need_approval_from = Group.objects.filter(name__in=["Finance", "IT"])

    if len(order.approvers) < 2:
        order.set_pending()

    if not order.all_groups_approved(need_approval_from):
        order.set_pending()

    return "SUCCESS", "", ""
