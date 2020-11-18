from django.conf.urls import url
from xui.content_export import views

xui_urlpatterns = [
    url(r'^content_export/export_content_list/$', views.export_content_list,
        name='export_content_list'),
    url(r'content_export/export_content_edit/(?P<id>\d+)/(?P<collections>[\w-]+)/$', views.export_content_edit,
        name='export_content_edit')
]