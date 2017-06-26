#!/usr/bin/env python

import sys
from costs.models import render_rate
from orders.models import Order

from utilities.logger import ThreadLogger

RATE_THRESHOLD = '{{ rate_threshold }}'

"""
Plug-in example for an Orchestration Action at the "Order Approval" trigger
point.  This bases approval on whether the order exceeds a rate threshold that is set in the CB
UI for this hook point.

If the order is below the threshold, the order is auto-approved by this plug-in.

If the order exceeds that threshold, this plug-in adds a comment to the order indicating that it
needs manual approval and why.

`order`: the order to be approved or denied.
`job`: always None in this context.
`logger`: write messages to the log for this action.
"""


def run(order, job=None, logger=None):
    if order.status != 'PENDING':
        logger.info('Order approval plugin skipped because order is not pending approval (it '
                    'is "{}").'.format(order.status))
        return '', '', ''

    if order.rate < RATE_THRESHOLD:
        order.approve()
    else:
        reason = 'This order requires manual approval as its rate ({}) exceeded the threshold of ' \
                 '{}'.format(render_rate(order.rate), render_rate(RATE_THRESHOLD))
        order.comment = reason
        order.save()
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
