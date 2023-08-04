from django.conf.urls import url
from xui.git_management import views


xui_urlpatterns = [
    url(
        r"^git_management/git_config/(?P<config_type>.*)/create/$",
        views.create_git_config,
        name="git_config_create",
    ),
    url(
        r"^git_management/git_config/(?P<config_type>.*)/edit/(?P<config_name>.*)/$",
        views.edit_git_config,
        name="git_config_edit",
    ),
    url(
        r"^git_management/git_config/(?P<config_type>.*)/delete/(?P<config_name>.*)/$",
        views.delete_git_config,
        name="git_config_delete",
    ),
    url(
        r"^git_management/commits/(?P<content_type>.*)/(?P<content_id>.*)/$",
        views.create_git_commit,
        name="git_commit_create",
    ),
    url(
        r"^git_management/commits/(?P<content_type>.*)/export_multiple$",
        views.export_multiple,
        name="export_multiple",
    ),
]

