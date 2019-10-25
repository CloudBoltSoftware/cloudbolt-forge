from django.conf.urls import url
from xui.dynamic_resource_groups.views import EditDynamicGroupRuleView

xui_urlpatterns = [
    url(
        r"^groups/(?P<group_id>\d+)/dynamic_rule/(?P<field_id>\d+)/edit/$",
        EditDynamicGroupRuleView.as_view(),
        name="dynamic_group_edit_rule",
    )
]
