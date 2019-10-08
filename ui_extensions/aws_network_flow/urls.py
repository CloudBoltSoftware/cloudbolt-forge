from django.conf.urls import url
from xui.aws_network_flow import views


xui_urlpatterns = [
    url(r'^aws_net_flows/(?P<handler_id>\d+)/$', views.aws_net_flows_json, name='aws_net_flows_json'),
]
