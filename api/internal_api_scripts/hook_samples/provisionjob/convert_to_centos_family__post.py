"""
If the OS Build name contains "Cent" (with any capitalization), change the OS
Family for the server to Linux -> CentOS. Useful to correct C2's notion of what
OS Family the server is when one needs to falsely set the guest ID on templates
to RedHat to enable network customization.

TODO: also change the guest ID in VMware
"""
import logging
import re

from externalcontent.models import OSFamily

logger = logging.getLogger(__name__)


def run(job, logger=None):
    if job.status != "SUCCESS":
        return "", "", ""

    server = job.server_set.all()[0]
    if not re.search("cent", server.os_build.name, re.I):
        # the server's OS does not include "cent", so we will leave it be
        return "", "", ""

    centosfam = OSFamily.objects.filter(name__iendswith="centos")[0]
    server.os_family = centosfam
    server.save()

    # TODO: set the guestOS in VMware

    return "", "", ""
