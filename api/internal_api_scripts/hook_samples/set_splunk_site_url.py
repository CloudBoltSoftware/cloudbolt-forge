#!/usr/local/bin/python

from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, *args, **kwargs):

    if job.status == 'SUCCESS' and is_splunk_server(job):
        server = job.server_set.first()
        set_site_url(server)

    return "", "", ""


def set_site_url(server):

    cf, created = CustomField.objects.get_or_create(
        type="URL",
        name='site_url')
    if created:
        cf.label = 'Splunk Site URL'
        cf.show_on_servers = True
        cf.save()

    url = 'http://{}:8000/'.format(server.ip)
    server.set_value_for_custom_field('site_url', url)
    logger.info('Splunk site url set to {}'.format(url))


def is_splunk_server(job):
    apps = job.job_parameters.cast().applications.all()
    if any('splunk' in app.name for app in apps):
        return True
    return False


if __name__ == '__main__':
    import sys
    from jobs.models import Job
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    job.status = 'SUCCESS'
    job.save()
    print run(job)
