import json, os

from datetime import datetime, timedelta
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from orders.models import Order
from common.methods import last_month_day_info
from extensions.views import report_extension
from .forms import OrderRangeForm, SummaryRangeForm
from utilities.logger import ThreadLogger
from django.db.models import Count
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse


from tempfile import NamedTemporaryFile
from reportengines.internal.export_utils import CSVWrapper
from wsgiref.util import FileWrapper

logger = ThreadLogger("__name__")

@report_extension(title='Order Status', thumbnail='order_status.png')
def order_information_table_report(request):
    profile = request.get_user_profile()
    if not profile.super_admin:
        raise PermissionDenied('Only super admins can view this report.')

    # Default date range from 1st to last day of last month, as datetime (not .date())
    start, end = last_month_day_info()

    show_table = False
    column_headings = ['Date', 'Order Id', 'Blueprint Name', 'Status', 'Owner']
    rows = []

    if request.method == 'GET':
        form = OrderRangeForm(initial=dict(start_date=start, end_date=end, status=["SUCCESS"]))
    else:
        show_table = True
        form = OrderRangeForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['start_date']
            end = form.cleaned_data['end_date']
            sel_status = form.cleaned_data['status']
            logger.info(f"selected status = {sel_status}")

            for o in Order.objects.all():
                if start <= o.create_date <= end and o.status in sel_status:
                    bp_name = getattr(o.blueprint, 'name', o.name)
                    rows.append((
                        o.create_date.date(),  # This stays as date for display
                        o.id,
                        bp_name,
                        o.status,
                        o.owner.user.username
                    ))

    return render(request, 'order_report_xui/templates/table.html', dict(
        pagetitle='Order Status',
        report_slug='Order Status',
        intro="Displays order summary within selected date range and status.",
        show_table=show_table,
        table_caption='Orders created between {} and {}'.format(start.date(), end.date()),
        form=form,
        column_headings=column_headings,
        rows=rows,
        sort_by_column=0,
        unsortable_column_indices=[],
    ))

@report_extension(title='Order Status Summary',thumbnail='order_summary.png')
def order_summary_status_report(request):
    today = datetime.now()
    start_date = None
    end_date = None

    form = SummaryRangeForm(request.GET or request.POST)
    selected_range = "30d"

    if form.is_valid():
        selected_range = form.cleaned_data.get("range", "30d")

    logger.info(f"Request.GET = {request.GET}")
    logger.info(f"Request.POST = {request.POST}")



    if selected_range == "30d":
        start_date = today - timedelta(days=30)
    elif selected_range == "12m":
        start_date = today - relativedelta(months=12)
    elif selected_range.startswith("month-"):
        try:
            _, year, month = selected_range.split("-")
            start_date = datetime(int(year), int(month), 1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(seconds=1)
        except:
            pass  # fallback to None
    # No filtering for 'all'

    queryset = Order.objects.all()
    if start_date:
        queryset = queryset.filter(create_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(create_date__lt=end_date)

    items = (
        queryset.values('name', 'status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    column_headings = ["Name", "Status", "Count"]
    rows = [
        [item["name"] or "", item["status"], item["count"]]
        for item in items
    ]

    context = {
        "report_slug": "order_summary_status_report",
        "pagetitle": "Order Status Summary",
        "report_name": "Order Summary Information",
        "form": form,
        "column_headings": column_headings,
        "rows": rows,
        "show_table": True,
        "sort_by_column": 2,
        "unsortable_column_indices": [],
    }
    logger.info(f"Filtering by: {selected_range}, Start: {start_date}, End: {end_date}")


    return render(request, "order_report_xui/templates/table.html", context)
def order_summary_export(request):
    today = datetime.now()
    start_date = None
    end_date = None

    form = SummaryRangeForm(request.GET or request.POST)
    selected_range = "30d"

    if form.is_valid():
        selected_range = form.cleaned_data.get("range", "30d")

    logger.info(f"Request.GET = {request.GET}")
    logger.info(f"Request.POST = {request.POST}")



    if selected_range == "30d":
        start_date = today - timedelta(days=30)
    elif selected_range == "12m":
        start_date = today - relativedelta(months=12)
    elif selected_range.startswith("month-"):
        try:
            _, year, month = selected_range.split("-")
            start_date = datetime(int(year), int(month), 1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(seconds=1)
        except:
            pass  # fallback to None
    # No filtering for 'all'

    queryset = Order.objects.all()
    if start_date:
        queryset = queryset.filter(create_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(create_date__lt=end_date)

    items = (
        queryset.values('name', 'status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    column_headings = ["Name", "Status", "Count"]
    rows = [
        [item["name"] or "", item["status"], item["count"]]
        for item in items
    ]

    context = {
        "report_slug": "order_summary_export",
        "report_name": "Order Summary Export",
        "form": form,
        "column_headings": column_headings,
        "rows": rows,
        "show_table": True,
        "sort_by_column": 2,
        "unsortable_column_indices": [],
    }
    logger.info(f"Filtering by: {selected_range}, Start: {start_date}, End: {end_date}")

    if 'export-data' in request.POST.get('action'):
        writer = CSVWrapper()
        writer.writerow(column_headings)
        for row in items:
            writer.writerow([row['name'], row['status'], row['count']])

        f = NamedTemporaryFile('w', delete=False)
        f.write(writer.close_and_return_as_string())
        f.close()
        filename = f.name
        wrapper = FileWrapper(open(filename,'rb'))
        export_filename = f'order_summary_{selected_range}.csv'
        response = HttpResponse(wrapper, content_type='text/plain')
        response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = f'attachment; filename={export_filename}'
        os.remove(f.name)
        return response