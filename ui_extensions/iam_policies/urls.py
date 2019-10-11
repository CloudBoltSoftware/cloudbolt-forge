from django.conf.urls import url

from . import views

xui_urlpatterns = [
    url(r'^(?P<handler_id>\d+)/aws_iam_policy/discover/$', views.discover_aws_iam_policies, name='discover_aws_iam_policies'),
    url(r'^(?P<handler_id>\d+)/aws_iam_policy/(?P<policy_arn>.+)/(?P<policy_name>[\w\-]+)/detail/$', views.aws_iam_policy_detail, name='aws_iam_policy_detail'),
    url(r'^(?P<handler_id>\d+)/aws_iam_policy/add/$', views.add_aws_iam_policy, name='add_aws_iam_policy'),
]
