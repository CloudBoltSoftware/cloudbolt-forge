#!/usr/bin/env python
import sys
from costs.models import render_rate
from orders.models import Order

from utilities.logger import ThreadLogger

RATE_THRESHOLD = {{ rate_threshold }}

"""
Plug-in example for an Orchestration Action at the "Order Approval" trigger
point.  May change CloudBolt's default approval behavior to implement custom
logic or integrate with an external change management system.
The context passed to the plug-in includes the order.
If the order is already ACTIVE when this hook is executed, this indicates that
the order was previously auto approved. If that was not the case, the current
hook randomly approves or denies the order. This is a skeleton and will
need to be changed to match your particular environment.
Args:
`order`: the order to be approved or denied.
`job`: always None in this context.
`logger`: write messages to the log for this action.
"""


def run(order, job=None, logger=None):
    if order.status != 'PENDING':
        logger.info('Order approval plugin skipped because order is not pending approval (it '
                    'is "{}").'.format(order.status))
        return '', '', ''

    # number of servers to be provisioned by this order
    number_of_servers = order.prov_server_count()

    # "Order items" are the line items added to an order. They may be of
    # several types: ProvisionServerOrderItem, ServerModOrderItem,
    # InstallServiceOrderItem, ProvisionNetworkOrderItem, etc.
    # Not all of them involve servers.
    items = [oi.cast() for oi in order.orderitem_set.filter()]

    conforms = False

    rate = order.rate
    if rate < RATE_THRESHOLD:
        conforms = True

    if conforms:
        order.approve()
    else:
        reason = 'This order requires manual approval as its rate ({}) exceeded the threshold of ' \
                 '{}'.format(
            render_rate(rate), render_rate(RATE_THRESHOLD))
        order.comment = reason
        order.save()
        # order.deny(reason=reason)

    # Return 'success' response even if we have rejected the order, since this
    # plug-in action succeeded.
    return '', '', ''


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: %s <CloudBolt order id>\n" % (sys.argv[0]))
        sys.exit(2)
    order_id = sys.argv[1]
    order = Order.objects.get(pk=order_id)
    logger = ThreadLogger(__name__)
    status, msg, err = run(order, logger=logger)
    print "status, msg, err = ", (status, msg, err)