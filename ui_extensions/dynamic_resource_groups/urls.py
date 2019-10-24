from django.conf.urls import url
from xui.dynamic_resource_groups.views import (
    DynamicGroupRuleView,
    DynamicGroupPolicyView,
)

xui_urlpatterns = [
    url(
        r"^groups/(?P<group_id>\d+)/dynamic_rule/add/$",
        DynamicGroupRuleView.as_view(),
        name="dynamic_group_add_rule",
    ),
    url(
        r"^groups/(?P<group_id>\d+)/dynamic_policy/add/$",
        DynamicGroupPolicyView.as_view(),
        name="dynamic_group_add_policy",
    ),
]
