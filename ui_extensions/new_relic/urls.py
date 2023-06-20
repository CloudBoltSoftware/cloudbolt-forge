from django.conf.urls import url
from xui.new_relic import views

xui_urlpatterns = [
    url(r'^new_relic/add_credentials/$', views.add_credentials,
        name='add_new_relic_credentials'),
    url(r'^new_relic/verify_credentials/$', views.verify_new_relic_credentials,
        name='verify_new_relic_credentials'),
    url(r'^new_relic/delete_credentials/$', views.delete_new_relic_credentials,
        name='delete_new_relic_credentials'),
    url(r'^new_relic/edit_credentials/$', views.edit_new_relic_credentials,
        name='edit_new_relic_credentials'),

    url(r'^new_relic/install_agent/(?P<server_id>\d+)$', views.install_agent,
        name='install_new_relic_agent'),
    url(r'^new_relic/uninstall_agent/(?P<server_id>\d+)$', views.uninstall_agent,
        name='uninstall_new_relic_agent'),
]
