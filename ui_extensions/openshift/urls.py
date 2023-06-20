from django.conf.urls import url
from xui.openshift import views

xui_urlpatterns = [
    url(r'^openshift/add_credentials/$', views.add_credentials,
        name='add_openshift_credentials'),
    url(r'^openshift/edit_credentials/$', views.edit_openshift_credentials,
        name='edit_openshift_credentials'),
    url(r'^openshift/verify_credentials/$', views.verify_credentials,
        name='verify_openshift_credentials'),
    url(r'^openshift/delete_openshift_credentials/$', views.delete_credentials,
        name='delete_openshift_credentials'),
]
