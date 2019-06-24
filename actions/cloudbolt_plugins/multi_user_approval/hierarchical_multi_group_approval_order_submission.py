"""
Hierarchical, Multiple Group Approval: Order Submisison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires that users from two separate Groups approve an Order in a
specified order before it becomes Active.


Configuration
~~~~~~~~~~~~~
If the user that submitted this Order belongs to "Workers", this plugin
requires one of two scenarios:
    1) "Finance" and "IT" groups both have "Approval Permission" for "Workers";
    2) The approving users are Approvers in both Groups (i.e. "Finance" and
       "IT").

When adding or editing this plugin, "Workers" must be added to the "Groups"
field.


Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""

from accounts.models import Group


def run(order, *args, **kwargs):
    # This hook executes after an Order is submitted by a User in the "Workers"
    # Group.

    # Immediately after submission, the Order is assigned to "Finance" for
    # approval.
    order.groups_for_approval = Group.objects.get(name="Finance")
