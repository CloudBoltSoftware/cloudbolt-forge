import sys
import time
from orders.models import Order

"""
Skeleton Order Approval hook, which allows changing CloudBolt's default approval
behavior, possibly to integrate with a separate change management system.

If the order is already ACTIVE when this hook is executed, this indicates that
the order was previously auto approved. If that was not the case, the current
hook randomly approves or denies the order. This is a skeleton and will
need to be changed to match your particular environment.
"""


def run(order, job=None, logger=None):
    if int(time.time()) % 2 == 0:
        # Randomly approves or denies the order, replace this logic with your own
        order.approve()
        return "", "", ""
    else:
        order.deny()
        # Note: The hook was still successful, so we return an empty status,
        # even though we have rejected the order
        return "", "", ""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt order id>\n" % (sys.argv[0]))
        sys.exit(2)
    order_id = sys.argv[1]
    order = Order.objects.get(pk=order_id)
    status, msg, err = run(order)
