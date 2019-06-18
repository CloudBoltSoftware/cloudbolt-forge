"""
Two User Approval

Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action requires two users to approve an order before it is becomes Active.
"""

from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(order, *args, **kwargs):
    # Return the order's status to "PENDING" if fewer than two users have
    # approved it.
    if len(order.approvers) < 2:
        order.status = "PENDING"
        order.save()

    return "SUCCESS", "", ""
