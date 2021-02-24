import json

# from customer_settings import KUMO_API_KEY
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.azure_arm.models import AzureARMHandler
from resourcehandlers.models import ResourceHandler
from utilities.decorators import json_view
from utilities.logger import ThreadLogger
from xui.kumo_integration_kit.kumo_wrapper import KumoConnector, KUMO_WEB_HOST
from pdb import set_trace as breakpoint

logger = ThreadLogger(__name__)


def calc_date_range(timeframe):
    # "mtd",
    # "ytd",
    # "wtd",
    # "qtd",
    # "prev_month",
    # "prev_quarter",
    # "prev_week"
    # "last30days",
    # "yesterday"
    from datetime import date
    from datetime import timedelta

    today = date.today()
    start, end = today, today

    if timeframe == "yesterday":
        start = today - timedelta(days=1)
        end = start

    fmt = '%B %-d, %Y'
    return start.strftime(fmt), end.strftime(fmt)


# POST
@json_view
def cost_overview_for_rh_json(request):
    payload = json.loads(request.body)
    rh = ResourceHandler.objects.get(id=payload['rh_id']).cast()

    if isinstance(rh, AWSHandler):
        with KumoConnector() as conn:
            response = conn.get('/report_dashboards', json=payload)
            response.raise_for_status()

    elif isinstance(rh, AzureARMHandler):
        pass

    return process_cost_overview_data(response.json())


def process_cost_overview_data(data):
    r = data.get('response')

    f = filter(
        lambda i: i['type'] == 'current_month_cost',
        r["report_dashboard"])
    mtd = next(f)['grid_data']['total']

    f = filter(
        lambda i: i['type'] == 'one_year_forecast',
        r['report_dashboard']
    )
    year_forecast = next(f)['grid_data']['total']

    f = filter(
        lambda i: i['type'] == 'current_year_cost',
        r['report_dashboard']
    )
    ytd = next(f)['grid_data']['total']

    f = filter(
        lambda i: i['type'] == 'thirty_days_forecast',
        r['report_dashboard']
    )
    month_forecast = next(f)['grid_data']['total']

    f = filter(
        lambda i: i['type'] == 'thirty_days_cost_by_day',
        r['report_dashboard']
    )
    raw_data = next(f)['chart_data']['dataset'][0]['data']
    categories = [i['label'] for i in raw_data]
    values = [i['value'] for i in raw_data]

    f = filter(
        lambda i: i['type'] == 'twelve_months_cost_by_year',
        r['report_dashboard']
    )
    total_costs = next(f)['grid_data']['total']

    return {
        "total_costs": total_costs,
        "monthly_budget": "?",
        "mtd": mtd,
        "mtd_delta": r['month_to_date_percent'],
        "month_forecast": month_forecast,
        "month_forecast_delta": r['month_forecast_percent'],
        "ytd": ytd,
        "year_forecast": year_forecast,
        "cost_by_day": {'categories': categories, 'values': values},
    }


@json_view
def spend_details_for_rh_json(request):
    payload = json.loads(request.body)
    rh = ResourceHandler.objects.get(id=payload['rh_id']).cast()

    if isinstance(rh, AWSHandler):
        with KumoConnector() as conn:
            response = conn.get('/report_dashboards', json=payload)
            response.raise_for_status()

    elif isinstance(rh, AzureARMHandler):
        pass

    return process_spend_details_for_rh_json(response.json())


def process_spend_details_for_rh_json(data):
    r = data.get('response')

    start_date, end_date = calc_date_range('yesterday')

    f = filter(
        lambda i: i['type'] == 'twelve_months_cost_by_year',
        r["report_dashboard"])
    twelve_months_cost_by_year = next(f)['chart_data']['dataset'][0]['data']
    total = 0
    for i in twelve_months_cost_by_year:
        total += i['value']
    avg_monthly_spend = total / 12

    f = filter(
        lambda i: i['type'] == 'thirty_days_cost_by_day',
        r["report_dashboard"])
    thirty_days_cost_by_day = next(f)['chart_data']['dataset'][0]['data']
    total = 0
    for i in thirty_days_cost_by_day:
        total += i['value']
    avg_daily_spend = total / 12

    yesterdays_spend = thirty_days_cost_by_day[-1]['value']

    return {
        "yesterdays_spend": yesterdays_spend,
        "avg_daily_spend": format(avg_daily_spend, '.2f'),
        "avg_monthly_spend": format(avg_monthly_spend, '.2f')
    }


def process_cost_efficiency_for_rh_json(aws, payload):
    with KumoConnector(KUMO_WEB_HOST + "/api/service_advisers") as conn:
        response = conn.get('/get_dashboard_summary', json=payload)
        response.raise_for_status()
        stat_data = response.json()

    with KumoConnector() as conn:
        response = conn.get(
            '/report_dashboards/cost_efficiency_summery', json=payload)
        response.raise_for_status()
        chart_data = response.json()

    if aws:
        data = next(filter(lambda i: i['provider'] == 'AWS', stat_data), {})
    else:
        data = next(filter(lambda i: i['provider'] == 'Azure', stat_data), {})

    return {
        "monthly_benefit": data["potential_benefit"],
        "avg_efficiency": chart_data['report']['grid_data']['total'],
        "services_count": data["no_of_services"],
        "chart_data": chart_data['report']['chart_data'],
        "unused_resources": '',
        "resizable_resources": '',
    }


@json_view
def cost_efficiency_for_rh_json(request):
    payload = json.loads(request.body)
    rh = ResourceHandler.objects.get(id=payload['rh_id']).cast()

    if isinstance(rh, AWSHandler) or isinstance(rh, AzureARMHandler):
        return process_cost_efficiency_for_rh_json(
            isinstance(rh, AWSHandler), payload)
    else:
        return {
            "monthly_benefit": '?',
            "avg_efficiency": '?',
            "unused_resources": '?',
            "resizable_resources": '?',
            "services_count": '?',
        }


def generate_chart_data(api_data, name, dictionary):
    dictionary[name] = {"labels": [], "values": []}
    for row in api_data["chart_data"]["categories"][0]["category"]:
        dictionary[name]["labels"].append(row["label"])
        dictionary[name]["values"].append(row["value"])


@json_view
def charts_data_rh_json(request):
    payload = json.loads(request.body)
    rh = ResourceHandler.objects.get(id=payload['rh_id']).cast()
    charts_data = {}

    with KumoConnector() as conn:
        response = conn.get(
            '/report_dashboards/cost_efficiency_summery', json=payload)
        response.raise_for_status()
        generate_chart_data(
            response.json()['report'], 'cost_efficiency', charts_data)

    with KumoConnector() as conn:
        response = conn.get('/report_dashboards', json=payload)
        response.raise_for_status()
        api_data = response.json()["response"]["report_dashboard"]

    for x in api_data:
        if ("chart_data" in x):
            generate_chart_data(x, x["type"], charts_data)
            charts_data[x["type"]]['total'] = x["grid_data"]["total"]
            charts_data[x["type"]]['previous_spend'] = x["grid_data"]["previous_spend"] if 'previous_spend' in x["grid_data"] else None
        elif x['type'] == 'thirty_days_ri_overview':
            charts_data['thirty_days_ri_overview'] = {
                "data": x['overview_data']['utilization']['chart_data'],
                "used_reservations": x['overview_data']['utilization']['grid_data']['used_reservations'],
                "unused_reservations": x['overview_data']['utilization']['grid_data']['unused_reservations'],
            }

    return {
        "cost_efficiency_chart_data": charts_data["cost_efficiency"],
        "cost_by_year_chart_data": charts_data['twelve_months_cost_by_year'],
        "cost_by_day_chart_data": charts_data['thirty_days_cost_by_day'],
        "cost_by_service_chart_data": charts_data['thirty_days_cost_by_service'],
        "month_to_date": charts_data['current_month_cost_by_all_account']['total'],
        "year_to_date": charts_data['current_year_cost']['total'],
        "year_forecast": charts_data['one_year_forecast']['total'],
        "total_spend": charts_data['thirty_days_cost_by_account']['total'],
        "yesterday_spend": charts_data['current_month_daily_cost']['previous_spend'],
        "ri_utilization_chart_data": charts_data['thirty_days_ri_overview']['data'],
        "used_reservations": charts_data['thirty_days_ri_overview']['used_reservations'],
        "unused_reservations": charts_data['thirty_days_ri_overview']['unused_reservations'],
    }
