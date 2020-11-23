from django.conf.urls import url
from xui.data_dog import views

xui_urlpatterns = [
    # DataDog connection urls
    url(r'^datadog/add_credentials/$', views.add_credentials,
        name='add_data_dog_credentials'),
    url(r'^datadog/edit_credentials/$',views.edit_credentials, 
        name='edit_data_dog_credentials'),
    url(r'^datadog/delete_credentials/$', views.delete_credentials,
        name='delete_data_dog_credentials'),
    url(r'^datadog/verify_credentials/$', views.verify_credentials,
        name='verify_data_dog_credentials'),
    url(r'^datadog/install_agent/(?P<server_id>\d+)/$', views.install_agent,
        name='install_data_dog_agent'),
    url(r'^datadog/uninstall_datadog_agent/(?P<server_id>\d+)/$', views.uninstall_agent,
        name='uninstall_datadog_agent'),
]
