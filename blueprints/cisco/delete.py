from utilities.models import ConnectionInfo
from ucscsdk.ucschandle import UcscHandle
from ucsmsdk.ucshandle import UcsHandle


conn, _ = ConnectionInfo.objects.get_or_create(name='Cisco UCS')

try:
    handle = UcscHandle(conn.ip, conn.username, conn.password, conn.port)
except Exception:
    # not a UCS central server. Connect using UcsHandle
    handle = UcsHandle(conn.ip, conn.username, conn.password, conn.port)


def run(job, resource, *args, **kwargs):
    # Delete the Service profile
    if not handle.cookie:
        handle.login()
    sp = handle.query_dn(f"{resource.service_profile_server_dn}")
    handle.remove_mo(sp)
    handle.commit()

    return "SUCCESS", "", ""
