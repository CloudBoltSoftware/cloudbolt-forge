from django.conf.urls import url

from xui.kumo_integration_kit.api import cost_overview_for_rh_json, \
    spend_details_for_rh_json, cost_efficiency_for_rh_json, charts_data_rh_json

xui_urlpatterns = [
    url(r"^xui/kumo/api/cost_overview_for_rh/$",
        cost_overview_for_rh_json, name="cost_overview_for_rh"),
    url(r"^xui/kumo/api/spend_details_for_rh/$",
        spend_details_for_rh_json, name="spend_details_for_rh"),
    url(r"^xui/kumo/api/cost_efficiency_for_rh/$",
        cost_efficiency_for_rh_json, name="cost_efficiency_for_rh"),
    url(r"^xui/kumo/api/charts_data_rh_json/$",
        charts_data_rh_json, name="charts_data_rh_json"),
]
