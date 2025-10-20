from django.conf.urls import url
from xui.order_report_xui import views

xui_urlpatterns = [
    url(r'^order_report_xui/order-summary/$', views.order_summary_status_report, name='order_summary_status_report'),
    url(r'^order_report_xui/order-summary/export/$', views.order_summary_export, name='order_summary_export'),
]