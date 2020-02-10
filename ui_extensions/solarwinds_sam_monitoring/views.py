"""SolarWinds Server Tab Views"""
from datetime import datetime
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from dateutil import tz
from dateutil.tz import tzlocal
from dateutil.tz import gettz
from django.shortcuts import get_object_or_404, render
from orionsdk import SwisClient
from requests.packages.urllib3 import disable_warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from extensions.views import tab_extension
from infrastructure.models import Server
from utilities.models import ConnectionInfo

# <monitoring_tab_view>
@tab_extension(model=Server, title='Monitoring', description='SolarWinds Monitoring')
def monitoring_tab_view(request, obj_id):
    """Render Server Monitoring Tab"""
    template_name = "solarwinds_sam_monitoring/templates/monitoring.html"

    try:
        # Get connection values
        sam = ConnectionInfo.objects.get(name='SolarWinds SAM')

        # Get node name and id
        node_name = get_object_or_404(Server, pk=obj_id).hostname

        # Get context sam.ip, sam.username, sam.password)
        context = get_context_data(node_name, sam.ip, sam.username, sam.password)

    except UnknownNodeName:
        # Change to alert template
        template_name = 'solarwinds_sam_monitoring/templates/monitoring_alert.html'
        # Put together alert context
        context = {
            'alert_type': 'warning',
            'alert_message': 'This system is not monitored by SolarWinds.'
        }

    except MultipleNodeIDsForNodeName:
        # Change to alert template
        template_name = 'solarwinds_sam_monitoring/templates/monitoring_alert.html'
        # Put together alert context
        context = {
            'alert_type': 'danger',
            'alert_message': "Error: Multiple nodes match the system's name."
        }

    except QueryError:
        # Change to alert template
        template_name = 'solarwinds_sam_monitoring/templates/monitoring_alert.html'
        # Put together alert context
        context = {
            'alert_type': 'danger',
            'alert_message': 'Error: An unexpected error occured.'
        }

    # render the page
    return render(request, template_name, context)

# </monitoring_tab_view>

# <get_context_data>
def get_context_data(node_name, sam_server, username, password):
    """Put together the context data"""

    # disable SSL warnings and connect to SolarWinds
    disable_warnings(category=InsecureRequestWarning)
    swis = SwisClient(hostname=sam_server, username=username, password=password)

    # Get node id
    node_id = get_node_id(swis=swis, node_name=node_name)

    # Put together context
    context = {}
    context['server_url'] = get_server_url(swis=swis)
    context['node_details'] = get_node_details(swis=swis, node_id=node_id)
    context['availability'] = get_availability(swis=swis, node_id=node_id)
    context['applications'] = get_applications(swis=swis, node_id=node_id)
    context['volumes'] = get_volumes(swis=swis, node_id=node_id)
    context['active_alerts'] = get_active_alerts(swis=swis, node_id=node_id)
    context['last_25_events'] = get_last_25_events(swis=swis, node_id=node_id)

    # Return the context
    return context

# </get_context_data>

# <get_server_url>
def get_server_url(swis):
    """Get Base Server URL"""

    # Get information from SolarWinds
    results = get_solarwinds_results(swis=swis, select=1, query=(
        "SELECT WebsiteID, ServerName, IPAddress, Port, Type, SSLEnabled "
        "FROM Orion.Websites "
        "WHERE Type = 'primary' "
        "ORDER BY SSLEnabled DESC "
    ))

    # Gather results
    server_name = results.get('ServerName')
    ssl_enabled = results.get('SSLEnabled')
    port_no = results.get('Port')

    # Verify results
    if not(server_name and isinstance(ssl_enabled, int) and port_no):
        raise RuntimeError('Unable to retreive website information from SolarWinds server.')

    # Put together and return results
    if ssl_enabled and port_no == 443:
        return "https://{}".format(server_name)
    elif ssl_enabled:
        return "https://{}:{}".format(server_name, port_no)
    elif port_no == 80:
        return "http://{}".format(server_name)
    else:
        return "http://{}:{}".format(server_name, port_no)

# </get_server_url>

# <get_node_id>
def get_node_id(swis, node_name):
    """Get Node ID"""

    # Get information from SolarWinds
    results = get_solarwinds_results(swis=swis, query=(
        "SELECT NodeID "
        "FROM Orion.Nodes "
        "WHERE Caption = '{0}' OR Caption LIKE '{0}.%'".format(node_name)
    ))

    # Validate results
    if not results:
        raise UnknownNodeName(
            'Node "{}" appears to be unmanaged.'.format(node_name)
        )
    elif len(results) > 1:
        raise MultipleNodeIDsForNodeName(
            'Multiple nodes found matching name "{}".'.format(node_name)
        )
    elif 'NodeID' not in results[0]:
        raise QueryError(
            'SWIS Query Error, missing NodeID key.'
        )

    # Return results
    return results[0]['NodeID']

# </get_node_id>

# <get_node_details>
def get_node_details(swis, node_id):
    """Get Node Details"""

    # Get information from SolarWinds
    result = get_solarwinds_results(swis=swis, select=1, query=(
        "SELECT N.NodeId, N.DetailsUrl, N.StatusIcon, N.StatusDescription, N.IPAddress, "
        "    N.DynamicIP, N.VendorIcon, N.MachineType, N.IsServer, N.DNS, N.SysName, "
        "    N.LastBoot,  N.SystemUpTime, N.IOSVersion, N.IOSImage, "
        "    H.HostName AS \"VMHostName\", H.DetailsUrl AS \"VMHostDetailsUrl\", "
        "    N.SNMPVersion, N.PollInterval, N.NextPoll "
        "FROM Orion.Nodes AS N "
        "    LEFT OUTER JOIN Orion.VIM.VirtualMachines AS VM "
        "        ON N.NodeID = VM.NodeID "
        "    LEFT OUTER JOIN Orion.VIM.Hosts AS H "
        "        ON VM.HostID = H.HostID "
        "WHERE N.NodeId = '{}'".format(node_id)
    ))

    # Put together the node details from the result
    node_details = {}
    node_details['url'] = result.get('DetailsUrl', '/Orion/SummaryView.aspx')
    node_details['status_icon'] = (
        '/Orion/images/StatusIcons/' + result.get('StatusIcon', 'unknown.gif')
    )
    node_details['status_text'] = result.get('StatusDescription', 'Unknown').replace(
        'Node status is', 'Node is'
    )
    node_details['polling_ip'] = result.get('IPAddress', '')
    node_details['dynamic_ip'] = result.get('DynamicIP', '')
    node_details['machine_type_icon'] = (
        '/NetPerfMon/Images/Vendors/' + result.get('VendorIcon', 'Unknown.gif')
    )
    node_details['machine_type_text'] = result.get('MachineType', '')
    node_details['category'] = 'Server' if result.get('IsServer') else 'Other'
    node_details['dns'] = result.get('DNS', '')
    node_details['system_name'] = result.get('SysName', '')
    try:
        node_details['last_boot'] = (
            parse(result.get('LastBoot')).strftime('%A, %B %d, %Y %I:%M %p')
        )
    except AttributeError as ValueError:
        node_details['last_boot'] = ""
    node_details['software_version'] = result.get('IOSVersion', '')
    node_details['virtual_host_name'] = result.get('VMHostName', '')
    node_details['virtual_host_url'] = (
        result.get('VMHostDetailsUrl', '/Orion/SummaryView.aspx')
    )
    node_details['polling_method'] = 'SNMP' if result.get('SNMPVersion') else 'ICMP'
    node_details['polling_interval'] = result.get('PollInterval', '??')
    try:
        node_details['next_poll'] = (
            parse(result.get('NextPoll', '') + ' UTC').astimezone(
                tzlocal()).strftime('%I:%M %p')
        )
    except AttributeError as ValueError:
        node_details['next_poll'] = "Unknown"

    # Return the node details
    return node_details

# </get_node_details>

# <get_applications>
def get_applications(swis, node_id):
    """Get Applications"""

    # Get information from SolarWinds
    results = get_solarwinds_results(swis=swis, query=(
        "SELECT ApplicationID, DisplayName, NodeID, DetailsUrl, Status, StatusDescription "
        "FROM Orion.APM.Application "
        "WHERE NodeID = '{}'".format(node_id)
    ))

    # initalize application list
    applications = []

    # get application details
    for result in results:
        application = {}

        # get status icon
        if result.get('StatusDescription'):
            application['status_icon'] = (
                '/Orion/APM/images/StatusIcons/Small-App-{}.gif'.format(
                    result.get('StatusDescription'))
            )
        else:
            application['status_icon'] = '/Orion/APM/images/StatusIcons/Small-App-Unknown.gif'

        # get name
        application['name'] = result.get('DisplayName', 'Unknown')

        # get link
        application['link'] = result.get('DetailsUrl', '/Orion/NetPerfMon/alerts.aspx')

        # get status
        application['status'] = result.get('StatusDescription', 'Unknown')

        # add to application list
        applications.append(application)

    # return results
    return applications

# </get_applications>

# <get_volumes>
def get_volumes(swis, node_id):
    """Get Volumes"""

    # Get volumes from SolarWinds
    results = get_solarwinds_results(swis=swis, query=(
        "SELECT NodeID, VolumeID, Status, StatusIcon, Icon, Caption, Type, VolumeSize, "
        "VolumeSpaceUsed, VolumePercentUsed, DetailsUrl "
        "FROM Orion.Volumes "
        "WHERE NodeID = '{}' "
        "ORDER BY Type, Caption"
    ).format(node_id))

    # Initalize list of Volumes
    volumes = []

    # Format Volumes Context
    for result in results:
        # Put together details
        volume = {}
        volume['icon'] = '/NetPerfMon/images/Volumes/' + result.get('Icon', 'Unknown.gif')
        volume['status_icon'] = (
            '/Orion/images/StatusIcons/' + result.get('StatusIcon', 'unknown.gif')
        )
        volume['name'] = result.get('Caption', 'Unknown')
        volume['link'] = result.get('DetailsUrl', '/#')
        volume['size'] = get_size_string(result.get('VolumeSize', 0))
        volume['used'] = get_size_string(result.get('VolumeSpaceUsed', 0))

        # Process percent used
        used_percent = result.get('VolumePercentUsed', 0)
        if used_percent < 0:
            used_percent = 0
        volume['used_percent'] = '{:.0f}'.format(used_percent)

        # Process used status
        if used_percent > 97:
            volume['used_status'] = 'danger'
        elif used_percent > 90:
            volume['used_status'] = 'warning'
        else:
            volume['used_status'] = 'success'

        # add details to list
        volumes.append(volume)

    # Return results
    return volumes

# </get_volumes>

# <get_active_alerts>
def get_active_alerts(swis, node_id):
    """Get Active Alerts"""

    # Get alerts from SolarWinds
    results = get_solarwinds_results(swis=swis, query=(
        "SELECT AC.Name, AA.AlertObjectID, AA.TriggeredMessage, AO.EntityCaption, "
        "    AO.EntityDetailsUrl, DATETIME(SUBSTRING(AA.TriggeredDateTime,1,19)) as TriggeredDateTime, AO.RelatedNodeId, "
        "    AO.RelatedNodeCaption, AO.RelatedNodeDetailsUrl, AO.TriggeredCount, "
        "    AC.Description, AC.Severity "
        "FROM Orion.AlertActive AS AA "
        "    JOIN Orion.AlertObjects AS AO "
        "        ON AA.AlertObjectID = AO.AlertObjectID "
        "    JOIN Orion.AlertConfigurations AS AC "
        "        ON AO.AlertID = AC.AlertID "
        "WHERE AA.AlertActiveID NOT IN ( "
        "    SELECT AlertActiveID "
        "    FROM Orion.AlertActive "
        "    WHERE Acknowledged = \"True\""
        ") AND AO.RelatedNodeId = '{}'".format(node_id)
    ))

    # initalize list of alerts
    node_alerts = []

    # get alerts
    for result in results:
        # initalize node alert
        node_alert = {}

        # name and link
        node_alert['name'] = result.get('Name', 'Unknown')
        if result.get('AlertObjectID'):
            node_alert['link'] = (
                '/Orion/NetPerfMon/ActiveAlertDetails.aspx?NetObject=AAT:{}'.format(
                    result.get('AlertObjectID')
                )
            )
        else:
            node_alert['link'] = '/Orion/NetPerfMon/alerts.aspx'

        # message
        node_alert['message'] = result.get('TriggeredMessage')

        # triggered object and link
        node_alert['triggering_object'] = result.get('EntityCaption', 'Unknown')
        node_alert['triggered_object_link'] = (
            result.get('EntityDetailsUrl', '/Orion/NetPerfMon/alerts.aspx')
        )

        # get triggered time
        try:
            tzinfos = {"UTC": gettz("UTC")}
            triggered_datetime = parse(
                "{} UTC".format(result.get('TriggeredDateTime'))).astimezone()
        except AttributeError as ValueError:
            triggered_datetime = None

        if triggered_datetime:
            # triggered times and dates
            node_alert['triggered_date'] = triggered_datetime.strftime('%m/%d/%y')
            node_alert['triggered_time'] = triggered_datetime.strftime('%I:%M %p')
            node_alert['triggered_display'] = (
                triggered_datetime.strftime('%a, %d %b, %Y %I:%M %p %z')
            )

            # calc active times
            active_timedelta = datetime.now(tz=tzlocal()) - triggered_datetime
            days = active_timedelta.days
            hours = int(active_timedelta.seconds / 3600)
            mins = int((active_timedelta.seconds - hours * 3600) / 60)

            # store active times
            if days:
                node_alert['active_time'] = "{}d {}h {}m ago".format(days, hours, mins)
            elif hours:
                node_alert['active_time'] = "{}h {}m ago".format(hours, mins)
            else:
                node_alert['active_time'] = "{}m ago".format(mins)
        else:
            node_alert['triggered_date'] = ""
            node_alert['triggered_time'] = "Unknown"
            node_alert['triggered_display'] = "Unknown Trigger Time"
            node_alert['active_time'] = ""

        # get related node
        node_alert['related_node'] = result.get('RelatedNodeCaption')

        # add node alert to list
        node_alerts.append(node_alert)

    # return results
    return node_alerts

# </get_active_alerts>

# <get_last_25_events>
def get_last_25_events(swis, node_id):
    """Get Last 25 Events"""

    # Get alerts from SolarWinds
    results = get_solarwinds_results(
        swis=swis, query=(
            "SELECT TOP 25 EventTime, Message, EngineID, EventType "
            "FROM Orion.Events "
            "WHERE NetObjectID = {} AND NetObjectType = 'N' "
            "ORDER BY EventTime DESC"
        ).format(node_id)
    )

    # initalize list of events
    node_events = []

    # get events
    for result in results:
        # initalize node event
        node_event = {}

        # get event time
        try:
            node_event['event_time'] = parse(
                "{} UTC".format(result.get('EventTime'))
            ).astimezone(tzlocal()).strftime('%m/%d/%y %I:%M %p')
        except AttributeError as ValueError:
            node_event['event_time'] = ""

        # get icon
        event_type = result.get('EventType')
        if event_type:
            node_event['icon'] = "/NetPerfMon/images/Event-{}.gif".format(event_type)
        else:
            node_event['icon'] = "/NetPerfMon/images/Event-5000.gif"

        # get message
        node_event['message'] = result.get('Message', 'Unknown event')

        # add node event to list
        node_events.append(node_event)

    # return results
    return node_events

# </get_last_25_events>

# <get_availability>
def get_availability(swis, node_id):
    """Get Availability"""

    # Get some dates
    now = datetime.now()
    today = now.strftime('%Y-%m-%d 00:00:00')
    yesterday = (now - relativedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
    seven_days = (now - relativedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
    thirty_days = (now - relativedelta(days=30)).strftime('%Y-%m-%d 00:00:00')
    this_year = (now - relativedelta(years=1)).strftime('%Y-%m-%d 00:00:00')

    # Get alerts from SolarWinds
    result = get_solarwinds_results(
        swis=swis, select=1, query=(
            "SELECT NodeId, "
            "    ( "
            "        SELECT SUM(Availability*Weight)/SUM(Weight) AS Today "
            "        FROM Orion.ResponseTime "
            "        WHERE NodeId = {0} "
            "            AND ObservationTimestamp >= '{1}' "
            "    ) AS Today, "
            "    ( "
            "        SELECT SUM(Availability*Weight)/SUM(Weight) AS Yesterday "
            "        FROM Orion.ResponseTime "
            "        WHERE NodeId = {0} "
            "            AND ObservationTimestamp >= '{2}' "
            "            AND ObservationTimestamp < '{1}' "
            "    ) AS Yesterday, "
            "    ( "
            "        SELECT SUM(Availability*Weight)/SUM(Weight) AS Last7Days "
            "        FROM Orion.ResponseTime "
            "        WHERE NodeId = {0} "
            "            AND ObservationTimestamp >= '{3}' "
            "    ) AS Last7Days, "
            "    ( "
            "        SELECT SUM(Availability*Weight)/SUM(Weight) AS Last30Days "
            "        FROM Orion.ResponseTime "
            "        WHERE NodeId = {0} "
            "            AND ObservationTimestamp >= '{4}' "
            "    ) AS Last30Days, "
            "    ( "
            "        SELECT SUM(Availability*Weight)/SUM(Weight) AS Last365Days "
            "        FROM Orion.ResponseTime "
            "        WHERE NodeId = {0} "
            "            AND ObservationTimestamp >= '{5}' "
            "    ) AS Last365Days "
            "FROM Orion.Nodes "
            "WHERE NodeId = {0}"
        ).format(node_id, today, yesterday, seven_days, thirty_days, this_year)
    )

    # get the base availability url
    link = "/Orion/NetPerfMon/CustomChart.aspx?ChartName=Availability&NetObject=N:{}&Period={}"

    # put together the availability
    availability = {}
    try:
        availability['today'] = "{0:.3f}".format(float(result.get('Today', 0)))
        availability['today_link'] = link.format(node_id, "Today")
    except TypeError:
        availability['today'] = "0.000"
        availability['today_link'] = "#"

    try:
        availability['yesterday'] = "{0:.3f}".format(float(result.get('Yesterday', 0)))
        availability['yesterday_link'] = link.format(node_id, "Yesterday")
    except TypeError:
        availability['yesterday'] = "0.000"
        availability['yesterday_link'] = "#"

    try:
        availability['last_7_days'] = "{0:.3f}".format(float(result.get('Last7Days', 0)))
        availability['last_7_days_link'] = link.format(node_id, "Last%207%20Days")
    except TypeError:
        availability['last_7_days'] = "0.000"
        availability['last_7_days_link'] = "#"

    try:
        availability['last_30_days'] = "{0:.3f}".format(float(result.get('Last30Days', 0)))
        availability['last_30_days_link'] = link.format(node_id, "Last%2030%20Days")
    except TypeError:
        availability['last_30_days'] = "0.000"
        availability['last_30_days_link'] = "#"

    try:
        availability['last_365_days'] = "{0:.3f}".format(float(result.get('Last365Days', 0)))
        availability['last_365_days_link'] = link.format(node_id, "This%20Year")
    except TypeError:
        availability['last_365_days'] = "0.000"
        availability['last_365_days_link'] = "#"

    # return results
    return availability

# </get_availability>

# <get_solarwinds_results>
def get_solarwinds_results(swis, query, select=0):
    """Get SolarWinds SWIS Query Results"""

    # Get information from SolarWinds
    results = swis.query(query)

    # Validate and store results
    if not results:
        raise QueryError('SWIS Query Error, unknown response')
    elif not isinstance(results, dict):
        raise QueryError('SWIS Query Error, response incorrectly formated')
    elif 'results' not in results:
        raise QueryError('SWIS Query Error, response missing results')
    elif not isinstance(results['results'], list):
        raise QueryError('SWIS Query Error, results incorrectly formated')
    results = results['results']

    # Select and return results
    if select == 1:
        results = results[0]
    elif select > 1:
        results = results[:select]
    return results

# </get_solarwinds_results>

# <get_size_string>
def get_size_string(size):
    """Return string representation of bytes"""

    # byte conversion numbers
    mbyte = 1024 ** 2
    gbyte = 1024 ** 3
    tbyte = 1024 ** 4
    pbyte = 1024 ** 5

    # convert to float
    size = float(size)

    # get string
    if size / pbyte > 1:
        result = '{:.1f} PB'.format(size / pbyte)
    elif size / tbyte > 1:
        result = '{:.1f} TB'.format(size / tbyte)
    elif size / gbyte > 1:
        result = '{:.1f} GB'.format(size / gbyte)
    else:
        result = '{:.1f} MB'.format(size / mbyte)

    return result

# </get_size_string>

class UnknownNodeName(Exception):
    """Unknown Node Name Exception"""
    pass

class MultipleNodeIDsForNodeName(Exception):
    """Multiple Node IDs for Node Name Exception"""
    pass

class QueryError(Exception):
    """SWIS Query Exception"""
    pass
