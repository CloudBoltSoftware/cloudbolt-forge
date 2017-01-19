# UI Extensions
*A new framework in CloudBolt 6.1-alpha2 and better

An extension is a Python package structured like this:

    package_name/
        __init__.py - required, may contain a docstring about this package
        views.py  - Django views registered as extensions
        templates/  - optional custom templates used by the views
        forms.py - optional Django forms required by the package

Extension views are decorated to register themselves at one of 3 extension points:

    from extensions.views import dashboard_extension, tab_extension, report_extension

    @dashboard_extension
    def my_dash_panel(request):
        # Shown as a new panel on the dashboard.
        # Your rendered HTML is able to move itself to the desired location in
        # the dashboard using JavaScript. See samples for details.

    from accounts.models import Group
    @tab_extension(model=Group, title='Service Stats')
    def group_deployed_service_stats(request, obj_id):
        # Shown on group detail pages as a new tab named "Service Stats"
        # Tab extensions are currently supported on the following models:
        #    accounts.models.Group
        #    infrastructure.models.Environment
        #    infrastructure.models.Server
        #    servicecatalog.models.ServiceBlueprint

    @report_extension
    def underutilized_servers_by_group(request):
        # Shown in the Reports menu.
        # CloudBolt ships with some templates to simplify development of report
        # extensions for pie, bar, and tabular reports.  Other charts are
        # available with a little extra work using the installed Highcharts
        # library API.


To install a package:
  * Download or create an extension package folder from the forge
  * Zip it up **including the folder name**.
  * Go to *Admin > Manage UI Extensions* and **upload** the zip file
  * (for now) restart Apache via `service httpd restart`

To customize:
  * Go to Admin > Manage UI Extensions and download the package
  * Unzip it and modify views as needed
  * Re-install it

Installed extension packages are located in /var/opt/cloudbolt/proserv/xui/<package_name>.  Any changes to those files take effect in the UI after Apache is restarted.
