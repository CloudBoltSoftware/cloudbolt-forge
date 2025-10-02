from django.conf.urls import url
from . import views

xui_urlpatterns = [
    url(
        r"^ssm-inventory/(?P<server_id>\d+)/inventory-json/$",
        views.inventory_json,
        name="ssm_inventory_json",
    ),
    url(
        r"^ssm-inventory/(?P<server_id>\d+)/patch-ec2/$",
        views.patch_ec2,
        name="ssm_inventory_patch_ec2",
    ),
    url(
        r"^ssm-inventory/(?P<server_id>\d+)/patch-json/$",
        views.patch_json,
        name="ssm_patch_json",
    ),
]