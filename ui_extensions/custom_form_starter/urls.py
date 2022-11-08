from django.conf.urls import url

from xui.custom_form_starter import views

xui_urlpatterns = [
    url(
        r"^custom_form/(?P<blueprint_id>\d+)/",
        views.get_custom_form,
        name="get_custom_form",
    ),
    url(
        r"^custom_form/deploy/", views.blueprint_deploy, name="deploy_custom_form"
    ),
    url(
        r"^ajax/custom_form/",
        views.get_custom_form_from_file,
        name="get_custom_form_from_file",
    ),
]
