from accounts.models import UserProfile
from utilities.logger import ThreadLogger
from utilities.mail import email
import csv, datetime
import tempfile
from reportengines.internal.export_utils import CustomServerReportTableConfig
from infrastructure.models import Server
CUSTOM_SERVER_REPORT_FILTERS_FORMSET_PREFIX = "filter_formset"
logger = ThreadLogger(__name__)


def run(job=None, **kwargs):
    # The current time, used to build date strings
    now = datetime.datetime.now()
    one_week_ago = now - datetime.timedelta(days=7)

    start_str = '{}-{:02d}-{}'.format(one_week_ago.year, one_week_ago.month, one_week_ago.day)
    end_str = '{}-{:02d}-{}'.format(now.year, now.month, now.day)
    profile_id = "{{ profile_id }}"
    requestor_email = "{{ email_recipient }}"
    profile = UserProfile.objects.get(id=profile_id)
    columns = ['Server', 'IP', 'Status', 'Owner', 'Group', 'Environment', 'Added']
    servers = Server.objects_for_profile(profile)
    servers = servers.exclude(status__in=["HISTORICAL"])
    servers = servers.filter(group__name='Unassigned')
    report_format = 'csv'
    table_config = CustomServerReportTableConfig(
                profile, columns, plain_text=False if report_format == "json" else True
            )
    table_config.aggregate_unfiltered_qs(servers)       
    rows = table_config.get_rows(servers)

    file = tempfile.NamedTemporaryFile()

    with open(file.name, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(table_config.get_column_headings())
        for l in rows:
            writer.writerow(l)

    with open(file.name, 'r') as f:
        email_attachments = [('{}_{}_{}.csv'.format('CustomServerReport', start_str, end_str), f.read(), 'text/csv')]

    email_context = {'subject': 'Custom Server Report',}
    recipients = requestor_email

    email(
        recipients=recipients,
        attachments=email_attachments,
        context=email_context,
    )

    file.close()
    
    return "", "", ""
