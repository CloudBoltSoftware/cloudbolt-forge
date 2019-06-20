"""
Hierarchical, Multiple Group Approval: Pre-Order Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
    # This hook executes after an Order has been approved by a user.

    group_b = Group.objects.get(name="Group_B")
    group_c = Group.objects.get(name="Group_C")
    group_d = Group.objects.get(name="Group_D")

    # If at least one user from Group_B has approved this order, assign the
    # order to "Group C" for approval.
    if (
        len(order.approvers) >= 1
        and order.approvers_group_contains([group_b])
    ):
        order.approval_groups = group_c
    # The order was approved, but the above conditions were not met. Return the
    # order's status to "PENDING", allowing other users to approve the order.
    else:
        order.set_pending()

    # If at least two users have approved this order, represting both Groups B
    # and C, assign the order to "Group D" for approval.
    if (
        len(order.approvers) >= 2
        and order.approvers_group_contains([group_b, group_c])
    ):
        order.approval_groups = group_d
    else:
        order.set_pending()

    # If at least three users have approved this order, represting Groups B, C,
    # and D, allow the order to be approved.
    if (
        len(order.approvers) >= 3
        and order.approvers_group_contains([group_b, group_c, group_d])
    ):
        pass
    else:
        order.set_pending()

    return "SUCCESS", "", ""
