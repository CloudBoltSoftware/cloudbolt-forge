import sys
import time
from orders.models import Order

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
        logger.info('Order approval plugin skipped because order is not pending approval.')
        return '', '', ''

    owner = order.owner
    group = order.group
    env = order.environment

    # number of servers to be provisioned by this order
    number_of_servers = order.prov_server_count()

    # "Order items" are the line items added to an order. They may be of
    # several types: ProvisionServerOrderItem, ServerModOrderItem,
    # InstallServiceOrderItem, ProvisionNetworkOrderItem, etc.
    # Not all of them involve servers.
    items = [oi.cast() for oi in order.orderitem_set.filter()]

    conforms = False
    # Add your logic to determine if this order conforms to your policies

    if conforms:
        order.approve()
    else:
        order.deny(reason='Sorry, your order was invalid because...')

    # Return 'success' response even if we have rejected the order, since this
    # plug-in action succeeded.
    return '', '', ''
