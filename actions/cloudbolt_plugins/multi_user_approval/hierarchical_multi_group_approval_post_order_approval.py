"""
Hierarchical, Multiple Group Approval: Post-Order Approval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
    # This hook executes after an Order has been approved by a user.

    finance_group = Group.objects.get(name="Finance")
    it_group = Group.objects.get(name="IT")

    # If at least one user from "Finance" has approved this order, assign the
    # order to "IT" for approval.
    if (
        len(order.approvers) >= 1
        and order.all_groups_approved([finance_group])
    ):
        order.groups_for_approval = it_group
    # The order was approved, but the above conditions were not met. Return the
    # order's status to "PENDING", allowing other users to approve the order.
    else:
        order.set_pending()

    # If at least two users have approved this order, represting both "Finance"
    # and "IT" Groups, allow the order to be approved.
    if (
        len(order.approvers) >= 2
        and order.all_groups_approved([finance_group, it_group])
    ):
        pass
    else:
        order.set_pending()

    return "SUCCESS", "", ""
