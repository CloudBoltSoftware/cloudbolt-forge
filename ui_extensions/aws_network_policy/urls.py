from django.conf.urls import url
from xui.aws_network_policy import views

xui_urlpatterns = [
    url(r'^aws_network_policy/server/(?P<server_id>\d+)/$', views.aws_network_policy_server_json,
        name='aws_network_policy_server_json'),
    url(r'^aws_network_policy/rh/(?P<rh_id>\d+)/$', views.aws_network_policy_rh_json,
        name='aws_network_policy_rh_json'),
]
