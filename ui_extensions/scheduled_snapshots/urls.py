from django.conf.urls import url

from xui.scheduled_snapshots import views

xui_urlpatterns = [
    url(r'^snapshots/configure_schedule/(?P<server_id>\d+)/$', views.configure_snapshot_schedule,
        name='configure_snapshot_schedule'),
    url(r'^snapshots/configure_max/(?P<server_id>\d+)/$',
        views.configure_snapshot_max, name='configure_snapshot_max'),
    url(
        r"^snapshots/revert/(?P<server_id>\d+)/(?P<snapshot_id>\d+)/$",
        views.server_revert_to_specific_snapshot,
        name="server_revert_to_specific_snapshot",
    ),
    url(
        r"^snapshots/create/(?P<server_id>\d+)/$",
        views.server_create_snapshot_respect_max,
        name="server_create_snapshot_respect_max",
    ),
]
