from utilities.models import ConnectionInfo
from ucscsdk.ucschandle import UcscHandle
from ucsmsdk.ucshandle import UcsHandle


conn, _ = ConnectionInfo.objects.get_or_create(name='Cisco UCS')

try:
    handle = UcscHandle(conn.ip, conn.username, conn.password, conn.port)
except Exception:
    # not a UCS central server. Connect using UcsHandle
    handle = UcsHandle(conn.ip, conn.username, conn.password, conn.port)


def get_all_organization(**kwargs):
    if not handle.cookie:
        handle.login()
    orgs = ['org-root']
    organizations = handle.query_children(in_dn="org-root", class_id="OrgOrg")
    orgs.extend([organization.dn for organization in organizations])
    handle.logout()
    return orgs


RESOURCE_IDENTIFIER = "service_profile_server_dn"


def discover_resources(**kwargs):
    discovered_service_profiles = []
    # Get all service profiles on UCS
    if not handle.cookie:
        handle.login()
    all_organizations = get_all_organization()
    for org in all_organizations:
        # Get the service profiles in an org.
        service_profiles = handle.query_children(in_dn=org, class_id="lsServer")
        for service_profile in service_profiles:
            discovered_service_profiles.append({
                "name": service_profile.dn.split("/")[-1],
                "service_profile_server_dn": service_profile.dn
            })

    return discovered_service_profiles
