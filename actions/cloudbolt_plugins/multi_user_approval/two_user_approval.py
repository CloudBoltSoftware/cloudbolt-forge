"""
Two User Approval
~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires two users to approve an Order before it becomes Active.


Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""


def run(order, *args, **kwargs):
    # Return the order's status to "PENDING" if fewer than two users have
    # approved it.

    if len(order.approvers) < 2:
        order.set_pending()

    return "SUCCESS", "", ""
