from django.conf.urls import url
from xui.solar_winds import views

xui_urlpatterns = [
    # SolarWinds REST connection urls
    url(r'^solarwinds/add_credentials/$', views.add_credentials,
        name='add_credentials'),
    url(r'^solarwinds/edit_credentials/$', views.edit_credentials,
        name='edit_credentials'),
    url(r'^solarwinds/delete_credentials/$',
        views.delete_credentials, name='delete_credentials'),
    url(r'^solarwinds/verify_connection/$', views.verify_credentials,
        name='verify_credentials'),

    # SolarWinds server connection urls
    url(r'^solarwinds/add_server_credentials/$', views.add_server_credentials,
        name='add_server_credentials'),
    url(r'^solarwinds/install_agent/(?P<server_id>\d+)$', views.install_agent,
        name='install_sam_agent'),
    url(r'^solarwinds/edit_server_credentials/$', views.edit_server_credentials,
        name='edit_server_credentials'),
    url(r'^solarwinds/delete_server_credentials/$', views.delete_server_credentials,
        name='delete_server_credentials'),
    url(r'^solarwinds/verify_server_connection/$', views.verify_server_credentials,
        name='verify_server_credentials'),

]
