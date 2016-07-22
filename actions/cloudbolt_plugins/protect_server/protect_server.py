from infrastructure.models import Server
from jobs.models import Job

TAG_NAME = 'protected'


def run(job, logger=None, **kwargs):
    '''
    This plugin should be attached to the pre-delete trigger to prevent the
    deletion of any server tagged in CloudBolt with a tag name corresponding
    to TAG_NAME. By default, this tag is named "protected".
    '''
    assert isinstance(job, Job)

    if job.type != 'decom':
        return "", "", ""

    s = job.server_set.first()
    assert isinstance(s, Server)

    if len(s.tags.filter(name=TAG_NAME)) > 0:
        return "FAILURE", "", "Server {} is protected, therefore it " \
                              "cannot be deleted.".format(s.hostname)

    return "", "", ""
