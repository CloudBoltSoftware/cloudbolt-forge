"""
Hierarchical, Multiple Group Approval: Order Approval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires that users from three separate Groups approve an Order in a
specified order before it becomes Active.


Configuration
~~~~~~~~~~~~~
If the user that submitted this Order belongs to Group_A, this plugin requires
one of two scenarios:
    1) Group B, Group C, and Group D all have "Approval Permission" for
       Group A;
    2) The approving users are Approvers in all four Groups (i.e. Groups A, B,
       C, and D).

When adding or editing this plugin, Group A must be added to the "Groups"
field.


Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""

from accounts.models import Group


def run(order, *args, **kwargs):
    # This hook executes after an Order is submitted by a User in Group A.

    # Immediately after submission, the Order is assigned to "Group B" for
    # approval.
    order.groups_for_approval = Group.objects.get(name="Group_B")
