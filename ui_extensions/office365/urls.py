from django.conf.urls import url
from xui.office365 import views

xui_urlpatterns = [
    url(r'^office365/add_credentials/$', views.add_credentials,
        name='add_office_credentials'),
    url(r'^office365/edit_credentials/$', views.edit_credentials,
        name='edit_office_credentials'),
    url(r'^office365/verify_credentials/$', views.verify_office_credentials,
        name='verify_office_credentials'),
    url(r'^office365/delete_credentials/$', views.delete_credentials,
        name='delete_office_credentials')
]
