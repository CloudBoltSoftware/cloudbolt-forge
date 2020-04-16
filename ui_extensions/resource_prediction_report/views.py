"""
Resource Use Prediction
~~~~~~~~~~~~~~~~~~~~~~~

Forecast use of specified resources given historical data.
"""

from django.shortcuts import render
from django.utils.translation import ugettext as _

from extensions.views import report_extension
from history.models import GlobalAllocationTotals
from utilities.models import GlobalPreferences

SUPPORTED_RESOURCES = {
    "servers": {"name": _("Servers")},
    "cpus": {"name": _("CPUs")},
    "memory": {"name": _("Memory"), "label": _("Memory in GB")},
    "disk": {"name": _("Disk"), "label": _("Disk in GB")},
    "rate": {
        "name": _("Rate"),
        "label": _("Rate in {currency}/{time}").format(
            currency=GlobalPreferences.get().rate_currency_unit,
            time=GlobalPreferences.get().get_rate_time_unit_display(),
        ),
    },
}


@report_extension(
    title="Resource Forecast", description="Forecast use of specified resources."
)
def create_prediction_report(request):
    """
    Returns rendered Resource Forecast report.
    """
    resource_type = request.GET.get("res", "servers")
    if resource_type not in list(SUPPORTED_RESOURCES.keys()):
        resource_type = "servers"
    resource = SUPPORTED_RESOURCES[resource_type]

    data = GlobalAllocationTotals.objects.make_plot_data(resource_type)
    predicted_data, r_squared = GlobalAllocationTotals.objects.predict_data(data, 3)

    series_data = [
        {
            "name": resource["name"],
            "label": resource.get("label", resource["name"]),
            "data": data,
        },
        {
            "name": "Prediction",
            "label": f"Predicted Value (r<sup>2</sup>={r_squared})",
            "data": predicted_data,
            "color": "#000000",
            "dashStyle": "Dash",
        },
    ]

    return render(
        request,
        "resource_prediction_report/templates/chart.html",
        {
            "pagetitle": _("{resource_name} Forecast").format(
                resource_name=resource["name"]
            ),
            "series_data": series_data,
            "resource": resource,
        },
    )
