"""
Threshold Check, Post-Order Approval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Overrides CloudBolt's standard Order Approval workflow. This Orchestration
Action checks if an Order crosses specified quota limits, and requires
different number of approvals depending on the cost.

If no threshold is exceeded, the Order is automatically approved. If any of the
configured values exceed 50%, but less than 90%, of the Group's quota, we
required one approver. If the configured values exceed 90% of the Group's
quota, we require that one user from the IT Group _and_ one user from the
Finance Group approve the order.


Configuration
~~~~~~~~~~~~~
In this example, we have three groups: Workers, IT, and Finance. Workers is a
sub-group of IT. Finance has been granted "Approval Permission" over Workers.
This Orchestration Action is enabled and configured to run for all orders
submitted by the Workers group.

Version Req.
~~~~~~~~~~~~
CloudBolt 8.8
"""

from accounts.models import Group


def create_combined_quota(order) -> dict:
    """
    Returns an updated version of the Order Group's quota dictionary, without
    modifying the database. Allows us to query the Order's effect on our
    configured quota limits.

    Returns:
        dict: Dictionary containing updated "available", "limit", "used", and
            "percent_used" data for each quota attribute.
    """
    group_quota = order.group.quota_set
    order_quota = order.net_usage()

    combined_quota = dict()
    for key, value in order_quota.items():
        group_quota_key = getattr(group_quota, key)
        d = {
            "limit": group_quota_key.limit,
            "used": group_quota_key.used + value,
        }
        d["percent_used"] = d["used"] / d["limit"]
        combined_quota[key] = d

    return combined_quota


def exceeds_quota_limit(quota_dict, threshold, attributes=[]) -> bool:
    """
    Returns True if one or more attributes exceed the specified percent-use
    threshold.

    Args:
        quota_dict (dict): Output from `create_combined_quota` function.
        threshold (float): Percentage (between 0 and 1) that attributes must
            not exceed.
        attributes (list, optional): List of values to check. If none are
            specified, all values are checked. Options are: "rate", "cpu_cnt",
            "mem_size", "disk_size", and "vm_cnt".

    Returns:
        bool: Returns True if any attributes violate the specified threshold.
            Otherwise, return False.
    """
    if not isinstance(attributes, list):
        raise ValueError("'attributes' must be a `list`.")

    if not (threshold >= 0 and threshold <= 1):
        raise ValueError("'threshold' must be between 0 and 1.")

    if attributes == []:
        attributes = quota_dict.keys()

    for attr in attributes:
        if quota_dict[attr]["percent_used"] >= threshold:
            return True

    return False


def run(order, *args, **kwargs):
    groups_that_must_approve = Group.objects.filter(
        name__in=["IT", "Finance"]
    )

    values_to_check = ["rate", "vm_cnt"]
    updated_quota = create_combined_quota(order)

    # If at least one of the values pushes our Group's quota to over 90% of its
    # configured limit, we will require that two users approve this order and
    # that users from both IT and Finance groups have approved it. If this has
    # not occurred, we call `order.set_pending()` and it will be returned to
    # the queue for our approvers.
    # Note: we call `return` here to avoid continuing into the next check.
    if exceeds_quota_limit(updated_quota, 0.9, values_to_check):
        if (
            len(order.approvers) >= 2
            and order.all_groups_approved(groups_that_must_approve)
        ):
            return "SUCCESS", "", ""
        else:
            order.set_pending()

    # If at least one of the values pushes our Group's quota to over 50% of its
    # configured limit, we required that one user approved the order. Because
    # we're in a "Post-Order Approval" action, that single approval has already
    # occurred, so we'll `pass`, allowing the order to be approved.
    elif exceeds_quota_limit(updated_quota, 0.5, values_to_check):
        pass

    return "SUCCESS", "", ""
