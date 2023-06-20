from collections import namedtuple
from django.shortcuts import get_object_or_404, render
from common.methods import columnify
from extensions.views import dashboard_extension
from operator import attrgetter
from django.contrib.auth.models import User
from orders.models import Order
import json
from extensions.views import report_extension
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, timedelta
from django.utils.translation import gettext as _


@report_extension(title='Orders History')
def display_orders(request):
    # Select period
    period = request.GET.get('period', 'month')
    periods = {'year': _('Year'), 'month': _('Month'), 'week': _('Week'), 'day': _('Day')}

    successful_orders_date = Order.objects.filter(status='SUCCESS').values_list('create_date', flat=True)
    failed_orders_date = Order.objects.filter(status='FAILURE').values_list('create_date', flat=True)
    cart_orders_date = Order.objects.filter(status='CART').values_list('create_date', flat=True)

    if period == "day":
        last_day = datetime.today() - timedelta(days=1)
        successful_orders_date = Order.objects.filter(status='SUCCESS', create_date__date__gte=last_day).values_list('create_date', flat=True)
        failed_orders_date = Order.objects.filter(status='FAILURE', create_date__date__gte=last_day).values_list('create_date', flat=True)
        cart_orders_date = Order.objects.filter(status='CART', create_date__date__gte=last_day).values_list('create_date', flat=True)
    elif period == "week":
        last_day = datetime.today() - timedelta(days=7)
        successful_orders_date = Order.objects.filter(status='SUCCESS', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        failed_orders_date = Order.objects.filter(status='FAILURE', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        cart_orders_date = Order.objects.filter(status='CART', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
    elif period == "month":
        last_day = datetime.today() - timedelta(days=30)
        successful_orders_date = Order.objects.filter(status='SUCCESS', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        failed_orders_date = Order.objects.filter(status='FAILURE', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        cart_orders_date = Order.objects.filter(status='CART', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
    elif period == "year":
        last_day = datetime.today() - timedelta(days=365)
        successful_orders_date = Order.objects.filter(status='SUCCESS', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        failed_orders_date = Order.objects.filter(status='FAILURE', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)
        cart_orders_date = Order.objects.filter(status='CART', create_date__date__gte=last_day).values_list(
            'create_date', flat=True)

    # count dates of orders
    successful_orders_count = count_orders(successful_orders_date)
    failed_orders_count = count_orders(failed_orders_date)
    cart_orders_count = count_orders(cart_orders_date)

    # list to pass to render
    success = to_dict(successful_orders_count)
    failure = to_dict(failed_orders_count)
    cart = to_dict(cart_orders_count)

    return render(request, 'orders_history/templates/charts.html', dict(
        pagetitle='Orders History',
        subtitle='Orders History',
        report_slug='orders_history',
        intro="""
                Sample Order Visualizer
            """,
        data_info=success,
        data_warning=cart,
        data_error=failure,
        periods=periods,
        current_period=period,
        series_name='orders'
    ))


def count_orders(list_of_dates):
    orders_count = {}
    for date in list_of_dates:
        day = date.date()
        if not day in orders_count:
            orders_count[day] = 1
        else:
            orders_count[day] += 1
    return orders_count


def to_dict(orders_count):
    result = []
    for date, count in orders_count.items():
        order_date = date.strftime("%x")
        order_date = datetime.strptime(order_date,"%m/%d/%y").timestamp()*1000
        success_dict = {'x': order_date, 'y': count}
        result.append(success_dict)
    return result
