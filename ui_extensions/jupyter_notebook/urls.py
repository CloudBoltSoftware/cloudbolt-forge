from django.conf.urls import url
from xui.jupyter_notebook import views

xui_urlpatterns = [
    url(r'^notebook', views.jupyter_notebook_view, name='django_notebook'),
    url(r'^restart_jupyterd', views.restart_jupyterd, name='restart_jupyterd')
]
