from django.conf.urls import url
from xui.azure_ad_group_import import views



xui_urlpatterns = [
    url(r'^azure_ad_group_import/$', views.ad_group_list, name='azure_ad_groups_list'),
    url(r'^azure_ad_group_import/create_cmp_group/$', views.create_cmp_group, name='create_cmp_group'),
    url(r'^azure_ad_group_import/(?P<group_id>[a-zA-Z0-9-]+)/$', views.group_detail, name='azure_group_detail'),
]
