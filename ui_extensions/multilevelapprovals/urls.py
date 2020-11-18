'''
    Pretty important to tell Django what url(s) you are masquerading as
'''
from __future__ import unicode_literals
from django.conf.urls import url
from .views import order_list
from . import views as multi_orders_views

xui_urlpatterns = [
    url(r'^orders/multi/$', view=order_list, name='Orders'),
    url(r'^orders/multi/(?P<order_id>\d+)/modify/$', multi_orders_views.modify, name='order_modify'),
    url(r'^orders/multi/json/$', multi_orders_views.order_list_json, name='order_list_json'),
]
urlpatterns = xui_urlpatterns
