from django.urls import path

from xui.cloudwatch_health.views import metrics_api

xui_urlpatterns = [
    path(
        "xui/cloudwatch_health/api/metrics/",
        metrics_api,
        name="cloudwatch_health_metrics",
    ),
]
