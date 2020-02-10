from django.conf.urls import url
from xui.aws_network_policy import views

xui_urlpatterns = [
    url(r'^aws_network_policy/server/(?P<server_id>\d+)/$', views.aws_network_policy_server_json,
        name='aws_network_policy_server_json'),
]
