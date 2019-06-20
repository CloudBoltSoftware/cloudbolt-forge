"""
Multiple Group Approval
~~~~~~~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires users from two separate Groups approve an Order before it
becomes Active.


Configuration
~~~~~~~~~~~~~
If the user that submitted this Order belongs to Group_A, this plugin requires
one of two scenarios:
    1) Both Group_B and Group_C have "Approval Permission" for Group_A;
    2) The approving users are Approvers in both Group_A and Group_B/Group_C.


Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""

from accounts.models import Group


def run(order, *args, **kwargs):
    approval_groups = Group.objects.filter(name__in=["Group_B", "Group_C"])

    if len(order.approvers) < 2:
        order.set_pending()

    if not order.approvers_group_contains(approval_groups):
        order.set_pending()

    return "SUCCESS", "", ""
