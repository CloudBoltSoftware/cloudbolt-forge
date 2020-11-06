from django.conf.urls import url
from xui.veeam import views

xui_urlpatterns = [
    url(r'^veeam/install_agent/(?P<server_id>\d+)/$',
        views.install_agent,
        name='install_agent'),
    url(r'^veeam/refresh_agent/(?P<server_id>\d+)/$',
        views.refresh_agent,
        name='refresh_agent'),
    url(r'^veeam/take_backup/(?P<server_id>\d+)/$',
        views.take_backup,
        name='take_backup'),

    # restore a backup
    url(r'^veeam/restore_backup/(?P<server_id>\d+)/(?P<restore_point_href>[\w-]+)/$',
        views.restore_backup,
        name='restore_backup'),
    # restore a backup to cloud
    url(r'^veeam/restore_backup_to_cloud/(?P<backup_name>.*)/$',
        views.restore_backup_to_cloud,
        name='restore_to_cloud'),

    # restore backup to ec2
    url(r'^veeam/restore_backup_to_ec2_cloud/(?P<backup_name>.*)/$',
        views.restore_backup_to_ec2_cloud,
        name='restore_to_ec2_cloud'),
    url(r'^veeam/get_aws_vpc/$',
        views.get_aws_vpc,
        name='get_aws_vpc'),
    url(r'^veeam/get_aws_security_groups/$',
        views.get_aws_security_groups,
        name='get_aws_security_groups'),
    url(r'^veeam/get_aws_availability_zones/$',
        views.get_aws_availability_zones,
        name='get_aws_availability_zones'),

    # VEEAM ConnectionInfo urls
    url(r'^veeam/create_endpoint/$', views.edit_veeam_endpoint,
        name='create_veeam_endpoint'),
    url(r'^veeam/edit_endpoint/(?P<endpoint_id>\d+)/$',
        views.edit_veeam_endpoint, name='edit_veeam_endpoint'),
    url(r'^veeam/delete_endpoint/$', views.delete_veeam_endpoint,
        name='delete_veeam_endpoint'),
    url(r'^veeam/verify_endpoint/$', views.verify_veeam_endpoint,
        name='verify_veeam_endpoint'),
]
