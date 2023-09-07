from django.conf.urls import url
from xui.jupyter_notebook_new import views

xui_urlpatterns = [
    url(r'^notebook_new', views.jupyter_notebook_new_view, name='django_notebook_new'),
]
