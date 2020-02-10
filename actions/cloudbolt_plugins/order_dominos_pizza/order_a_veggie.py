#!/usr/bin/env python

"""
To set this up, on your CB server:
 * `pip install usaddress`
 * `cd /var/opt/cloudbolt/proserv/`
 * `git clone https://github.com/gamagori/pizzapi.git`
 * `ln -s pizzapi-repo/pizzapi .`
 * possibly replace the tab characters on lines 107 and 130 of order.py with 8 spaces.

If you order this blueprint from CloudBolt, and it fails, check your email, it is possible that
the pizza order completed but there was an error when checking the status of the order.

Possible future improvements:
 * Parse the menu to generate realtime, store-specific menu options
 * Allow customization of menu items
"""

import time

import re
import usaddress

from pizzapi.payment import PaymentObject
from pizzapi.address import Address
from pizzapi.order import Order
from pizzapi.customer import Customer
from pizzapi.track import track_by_phone

from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def generate_options_for_store(control_value=None, **kwargs):
    if not control_value:
        return []
    try:
        _, store = parse_address(control_value)
    except Exception as err:
        logger.exception("error when trying to generate store option")
        return [str(err)]
    return [store.data['AddressDescription']]


def generate_options_for_pizza_type(control_value=None, **kwargs):
    # Eventually we could make the menu options depend on the address chosen, fetch the menu for
    # the closest store, and then filter it down to the options that do not require customization.
    # if not control_value:
    #     return []
    #
    # address = parse_address(control_value)
    # store = address.closest_store()
    # menu = store.get_menu()

    # For now, though, just return some hard coded, non-regional options
    return [
        ("P14IREPV", "Pacific Veggie"),
        ("P14IRECZ", "Wisconsin 6 Cheese"),
        ("P14IRESPF", "Spinach & Feta"),
    ]


def parse_address(full_address):
    """
    Takes a full_address string and return a 2-tuple of (pizzapi Address, pizzapi Store)
    """
    # address_type = "{ address_type }"  # pizzapi doesn't support this yet
    addr_parts = usaddress.tag(full_address)[0]
    addr_line_one = " ".join([
        addr_parts.get("AddressNumber", ""),
        addr_parts.get("StreetNamePreDirectional", ""),
        addr_parts.get("StreetName", ""),
        addr_parts.get("StreetNamePostType", ""),
        addr_parts.get("OccupancyType", ""),
        addr_parts.get("OccupancyIdentifier", ""),
    ])
    address = Address(
        addr_line_one, addr_parts["PlaceName"], addr_parts["StateName"], addr_parts["ZipCode"])
    store = address.closest_store()
    return address, store


def get_payment():
    cc_number = "{{ credit_card_number }}"
    cc_expiration = "{{ credit_card_expiration }}"
    cc_pin = "{{ credit_card_pin }}"
    cc_zip = "{{ credit_card_zip }}"
    return PaymentObject(cc_number, cc_expiration, cc_pin, cc_zip)


def wait_for_order(phone):
    """
    Loop and wait until the order is delivered
    :return: None
    """
    # Example status_dict that we get back from the API:
    # OrderedDict([('Version', '1.5'), ('AsOfTime', '2018-08-03T11:03:37'), ('StoreAsOfTime',
    # '2018-08-03T11:08:23'), ('StoreID', '7231'), ('OrderID', '2018-08-03#50446'), ('Phone',
    # '5035551234'), ('ServiceMethod', 'Delivery'), ('AdvancedOrderTime', None),
    # ('OrderDescription', '1 Large (14") Hand Tossed Pacific Veggie'),
    # ('OrderTakeCompleteTime', '2018-08-03T11:02:14'), ('TakeTimeSecs', '2'), ('CsrID',
    # 'Power'), ('CsrName', None), ('OrderSourceCode', 'Web'), ('OrderStatus', 'Oven'),
    # ('StartTime', '2018-08-03T11:02:14'), ('MakeTimeSecs', '83'), ('OvenTime',
    # '2018-08-03T11:03:37'), ('OvenTimeSecs', None), ('RackTime', None), ('RackTimeSecs', '0'),
    #  ('RouteTime', None), ('DriverID', None), ('DriverName', None), ('OrderDeliveryTimeSecs',
    # None), ('DeliveryTime', None), ('OrderKey', '723189446303'), ('ManagerID', '5298'),
    # ('ManagerName', 'Rachel')])
    order_status = ""
    prog_msg = ""
    while order_status != "Complete":
        try:
            status_dict = track_by_phone(phone)
        except TypeError:
            logger.exception("Failed to get order status, trying again in 10s.")
            time.sleep(10)
            continue
        order_desc = status_dict.get('OrderDescription', "")
        order_desc = order_desc.replace("\n", ", ")
        order_status = status_dict.get('OrderStatus', "")
        if order_status in ["Oven", "Routing Station"]:
            order_status = f"in the {order_status}."
        if order_status in ["Out the Door"]:
            driver_name = status_dict.get('DriverName', "")
            if driver_name:
                order_status = f"{order_status} with {driver_name}."
        new_prog_msg = f"Your order of {order_desc} is {order_status}"
        if new_prog_msg != prog_msg:
            prog_msg = new_prog_msg
            set_progress(prog_msg)
        time.sleep(10)


def show_delivery_wait_times(store_details):
    delivery_times = store_details['ServiceMethodEstimatedWaitMinutes']['Delivery']
    min = delivery_times['Min']
    max = delivery_times['Max']
    set_progress(f"Delivery time: {min}-{max} minutes")


def get_order_id(result):
    # This method is not currently used, but will be needed if we go back to tracking orders by
    # order ID instead of phone #.
    order_obj = result.get('Order', None)
    if not order_obj:
        logger.warning("Could not fetch the 'Order' key from the result.")
        return
    order_id = order_obj.get('OrderID', None)
    set_progress(f"Order ID: {order_id}")
    return order_id


def phone_number_to_int(phone):
    """
    Converts a string phone number to an integer, as needed by track_by_phone()

    >>> phone_number_to_int('503-555-1234')
    5035551234
    >>> phone_number_to_int('503.555.1234')
    5035551234
    """
    phone = re.sub(r"[\.-]", "", phone)
    return int(phone)


def run(job, *args, **kwargs):
    user = job.owner.user
    test_only = "{{ test_only }}" == "True"
    if test_only:
        set_progress(f"Only testing, will not order the pizza.")
    else:
        set_progress(f"This is not a test, the pizza will be ordered.")

    stuffed_cheesy_bread = "{{ stuffed_cheesy_bread }}" == "True"
    full_address = "{{ full_address }}"
    phone = "{{ recipient_phone }}"
    # For display purposes only, to show on the form with a generated option
    # This is in triple quotes because it is sometimes returned from the API w/ linebreaks in it
    _ = """{{ store }}"""
    address, store = parse_address(full_address)
    customer = Customer(user.first_name, user.last_name, user.email, phone, full_address)

    store_details = store.get_details()
    logger.info(f"store_details = {store_details}")
    set_progress(f"Found closest store at {store_details['StreetName']}")
    show_delivery_wait_times(store_details)

    set_progress("Constructing the order")
    order = Order(store, customer, address)
    set_progress("Adding the pizza ({{ pizza_type }}).")
    quantity = "{{ quantity }}" or "0"
    quantity = int(quantity)
    order.add_item("{{ pizza_type }}", qty=quantity)
    if stuffed_cheesy_bread:
        set_progress("Adding a stuffed cheesy bread.")
        order.add_item("B8PCSCB")

    set_progress("Constructing the payment.")
    card = get_payment()
    if test_only:
        set_progress('Testing the order!')
        result = order.pay_with(card)
    else:
        set_progress('Ordering!')
        result = order.place(card)
    # Remove the payment info before proceeding to ensure it is not logged
    result['Order'].pop('Payments', None)

    status = result['StatusItems'][0]['Code'].upper()
    logger.info(f"result = {result}")
    if status == "SUCCESS" and not test_only:
        phone = phone_number_to_int(phone)
        wait_for_order(phone)
        return status, "Delivered! Enjoy your pizza.", ""
    return status, "", ""


if __name__ == "__main__":
    import doctest
    doctest.testmod()
