from django.conf.urls import url
from . import views

xui_urlpatterns = [
    url(
        r"^azure-patches/(?P<server_id>\d+)/inventory-json/$",
        views.inventory_json,
        name="az_patches_inventory_json",
    ),
    url(
        r"^azure-patches/(?P<server_id>\d+)/patches/scan/$",
        views.scan_for_patches,
        name="az_scan_for_patches",
    ),
    url(
        r"^azure-patches/(?P<server_id>\d+)/patches/apply/$",
        views.apply_all_patches,
        name="az_apply_all_patches",
    ),
]