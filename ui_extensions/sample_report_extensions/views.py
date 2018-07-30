"""
Module contains all views for this extension package.
"""
import datetime

from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from accounts.models import Group
from common.methods import last_month_day_info, get_rh_html_display
from extensions.views import report_extension
from infrastructure.models import Environment
from utilities.permissions import cbadmin_required
from utilities.templatetags import helper_tags
from infrastructure.templatetags import infrastructure_tags

from .forms import DateRangeForm


# To install your own custom thumbnail image, say "pie_chart.png":
#
# 1. scp image file to /var/www/html/cloudbolt/static/uploads/extensions/pie_chart.png
# 2. run `/opt/cloudbolt/manage.py collectstatic --noinput`
# 3. change the decorator line below to this:
#     @report_extension(title='...', thumbnail='pie_chart.png')

@report_extension(title='Server Counts by Group (Pie)')
def sample_pie_report(request):
    """
    Demonstrates a basic pie chart report.
    """
    profile = request.get_user_profile()
    if not profile.super_admin:
        raise PermissionDenied('Only super admins can view this report.')

    # Run your custom report logic to build the following lists:
    # categories = ['Tullys', 'Tyrell', 'Lannister', 'Stark', 'Baratheon']
    # values = [85, 100, 250, 75, 42]
    categories = []
    values = []
    for group in Group.objects.all():
        active_servers = group.server_set.exclude(status='HISTORICAL')
        if active_servers:
            categories.append(group.name)
            values.append(active_servers.count())

    # This sample extension renders a generic template for pie charts,
    # which requires this view to return just a few context variables.
    #
    # You could also define your own template that extends one of the following
    # and adds customizations:
    #     'reports/pie.html' if you want a more customized pie chart
    #     'reports/simple_base.html' for more advanced customization, e.g. more
    #     than one chart or table.
    #     'base.html' to start from scratch from the basic CloudBolt template
    return render(request, 'reports/pie.html', dict(
        pagetitle='Server Counts by Group (Pie)',
        report_slug='Server Counts by Group',
        subtitle='Excludes historical servers',
        intro="""
            Sample report extension draws a pie chart.
        """,
        # Pie chart data
        categories=categories,
        values=values,
        series_name='Servers',
        # Optionally support exporting as CSV by including this dict
        export=dict(
            csv_headings=['Group', 'Active Servers']
        )
    ))


@report_extension(title='Server Counts by Group (Bar)')
def sample_bar_report(request):
    """
    Demonstrates a basic horizontal bar chart report.
    """
    profile = request.get_user_profile()
    if not profile.super_admin:
        raise PermissionDenied('Only super admins can view this report.')

    # Run your custom report logic to build the following lists:
    # categories = ['Tullys', 'Tyrell', 'Lannister', 'Stark', 'Baratheon']
    # values = [85, 100, 250, 75, 42]
    categories = []
    values = []
    for group in Group.objects.all():
        active_servers = group.server_set.exclude(status='HISTORICAL')
        if active_servers:
            categories.append(group.name)
            values.append(active_servers.count())

    # This sample extension renders a generic template for bar charts,
    # which requires this view to return just a few context variables.
    #
    # You could also define your own template that extends one of the following
    # and adds customizations:
    #     'reports/bar.html' if you want a more customized pie chart
    #     'reports/simple_base.html' for more advanced customization, e.g. more
    #     than one chart or table.
    #     'base.html' to start from scratch from the basic CloudBolt template
    return render(request, 'reports/bar.html', dict(
        pagetitle='Server Counts by Group (Bar)',
        subtitle='Excludes historical servers',
        report_slug='Server Counts by Group',
        intro="""
            Sample report extension draws a bar chart.
        """,
        # Chart data
        categories=categories,
        values=values,
        series_name='Servers',
        # Optionally support exporting as CSV by including this dict
        export=dict(
            csv_headings=['Group', 'Active Servers']
        )
    ))


@report_extension(title='Environment Server Stats')
def sample_table_report(request):
    """
    Draw a date range form and once it is posted include a tabular report.

    """
    profile = request.get_user_profile()
    if not profile.super_admin:
        raise PermissionDenied('Only super admins can view this report.')

    # Default date range from 1st to last day of last month, without time part
    start, end = last_month_day_info()
    start = start.date()
    end = end.date()

    # Hide table until form has been submitted
    show_table = False

    column_headings = [
        'Environment',
        'Resource Handler',
        'Most Recently Added Servers',
        'Windows Servers',
        'Other Servers',
    ]

    rows = []

    if request.method == 'GET':
        form = DateRangeForm(initial=dict(start_date=start, end_date=end))
    else:
        show_table = True

        form = DateRangeForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['start_date']
            end = form.cleaned_data['end_date']

            for env in Environment.objects.all():
                rh = None
                if env.resource_handler:
                    rh = env.resource_handler

                # Sort in DESC because server_cards below will show *last* 3
                active_servers = (
                    env.server_set
                        .exclude(status='HISTORICAL')
                        .filter(add_date__range=(start, end))
                        .order_by('-add_date')
                )

                win_servers = active_servers.filter(os_family__name='Windows')


                # Each row is a tuple of cell values
                rows.append((
                    helper_tags.render_link(env),
                    get_rh_html_display(rh, profile) if rh else '',
                    infrastructure_tags.server_cards(active_servers, profile, max_cards=3),
                    win_servers.count(),
                    active_servers.count() - win_servers.count(),
                ))
        else:
            # form will be re-rendered with validation errors
            pass

    # This sample extension renders a generic template for tabular reports,
    # which requires this view to return just a few context variables.
    #
    # You could also render your own template in '<package_name>/templates/special.html'
    # that extends one of the following and adds customizations:
    #     'reports/table.html' if you want a more customized data table
    #     'reports/simple_base.html' for more advanced customization, e.g. more
    #     than one chart or table.
    #     'base.html' to start from scratch from the basic CloudBolt template
    return render(request, 'reports/table.html', dict(
        pagetitle='Environment Server Stats',
        report_slug='Environment Server Stats',
        intro="""
            Sample report extension draws a table and demonstrates use of a form.
            Date range is used to filter servers to those added in that period.
        """,
        show_table=show_table,
        table_caption='Shows servers added between {} and {}'.format(start, end),
        form=form,
        column_headings=column_headings,
        rows=rows,
        # numeric column index (0-based) to sort by
        sort_by_column=2,
        # numeric column index (0-based) where sort is disabled
        unsortable_column_indices=[],
    ))
