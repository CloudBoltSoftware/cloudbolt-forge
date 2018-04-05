"""
Post-provision hook to confirm that a new Windows server has correctly joined
the requested AD domain.

Determines the correct domain based on the value of the domain_to_join Custom Field.
"""
import sys

from common.methods import set_progress


def run(job, **kwargs):
    """
    Gets the domain the Windows server has joined and confirms it is what we
    expect it to be
    """
    if job.status == 'FAILURE':
        set_progress('Domain verification hook skipped because job failed')
        return "", "", ""
    server = job.server_set.all()[0]
    if not server.os_build.is_windows():
        set_progress("Skipping domain verification for non-windows machine")
        # only run verification on windows VMs
        return "", "", ""

    expected_domain_obj = server.get_value_for_custom_field('domain_to_join')
    if not expected_domain_obj:
        set_progress("Skipping domain verification test since no "
                     "domain was specified")
        return "", "", ""

    expected_domain = expected_domain_obj.ldap_domain
    actual_domain = server.get_current_domain()

    if actual_domain == expected_domain:
        set_progress("Domain '{}' successfully set on server".format(actual_domain))
        return "", "", ""
    elif actual_domain is None:
        msg = (
            "Could not determine current domain. Be sure to provide either "
            "Windows Server Password or VMware Template Password parameter."
        )
        set_progress(msg)
        return "FAILURE", msg, ""
    else:
        msg = "Failed to join server to domain '{}', actual domain is '{}'".format(
            expected_domain, actual_domain)
        set_progress(msg)
        return "FAILURE", msg, ""


if __name__ == '__main__':
    job_id = sys.argv[1]

    from jobs.models import Job
    from utilities.logger import ThreadLogger
    logger = ThreadLogger(__name__)

    job = Job.objects.get(id=job_id)

    print(run(job, logger))
