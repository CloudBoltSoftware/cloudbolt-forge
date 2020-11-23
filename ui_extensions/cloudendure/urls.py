from django.conf.urls import url
from xui.cloudendure import views

xui_urlpatterns = [
    # CloudEndure connection urls
    url(r'^cloudendure/add_cloudendure_endpoint/$', views.add_cloudendure_endpoint,
        name='add_cloudendure_endpoint'),
    url(r'^cloudendure/edit_cloudendure_endpoint/$', views.edit_cloudendure_endpoint,
        name='edit_cloudendure_endpoint'),
    url(r'^cloudendure/delete_cloudendure_endpoint/$', views.delete_cloudendure_endpoint,
        name='delete_cloudendure_endpoint'),
    url(r'^cloudendure/verify_cloudendure_connection/$', views.verify_cloudendure_connection,
        name='verify_cloudendure_connection'),
    url(r'^cloudendure/install_cloudendure_agent/(?P<server_id>\d+)$', views.install_cloudendure_agent,
        name='install_cloudendure_agent'),

    # CloudEndure machine actions urls
    url(r'^cloudendure/cloudendure_machine_actions/(?P<server_id>\d+)/(?P<action>[\w-]+)/$', views.cloudendure_machine_actions,
        name='cloudendure_machine_actions'),


    # CloudEndure machine migration
    url(r'^cloudendure/cloudendure_machine_migration/(?P<project_id>[\w-]+)/(?P<machine_id>[\w-]+)/$', views.cloudendure_machine_migration,
        name='cloudendure_machine_migration'),
    # cloudendure projects
    url(r'^cloudendure/create_cloudendure_project/$', views.create_cloudendure_project,
        name='create_cloudendure_project'),

]
