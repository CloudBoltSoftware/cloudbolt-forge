from django.conf.urls import url
from xui.bolty_cards import views

xui_urlpatterns = [
    url(r'^bolty_cards/get_canvas/$', views.get_canvas, name='get_canvas'),
]