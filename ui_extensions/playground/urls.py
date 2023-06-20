from django.urls import path

from xui.playground.api import fetch_data_from_api

API_BASE = "xui/playground/api"

xui_urlpatterns = [
    path(f"{API_BASE}/data", fetch_data_from_api),
]
