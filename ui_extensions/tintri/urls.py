from django.conf.urls import url
from xui.tintri import views

xui_urlpatterns = [
    # ConnectionInfo urls
    url(r'^tintri/create_endpoint/$', views.edit_tintri_endpoint,
        name='create_tintri_endpoint'),
    url(r'^tintri/edit_endpoint/(?P<endpoint_id>\d+)/$',
        views.edit_tintri_endpoint, name='edit_tintri_endpoint'),
    url(r'^tintri/delete_endpoint/$', views.delete_tintri_endpoint,
        name='delete_tintri_endpoint'),
    url(r'^tintri/verify_endpoint/$', views.verify_tintri_endpoint,
        name='verify_tintri_endpoint'),
    url(r'^tintri/take_snapshot/(?P<server_id>\d+)/$',
        views.create_tintri_snapshot, name='create_tintri_snapshot'),
    url(r'^tintri/delete_snapshot/(?P<server_id>\d+)/(?P<snapshot_uuid>[\w-]+)/$',
        views.delete_tintri_snapshot, name='delete_tintri_snapshot'),
    url(r'^tintri/clone_from_snapshot/(?P<server_id>\d+)/(?P<snapshot_uuid>[\w-]+)/$',
        views.clone_from_tintri_snapshot, name='clone_from_tintri_snapshot'),
]
