#!/usr/local/bin/python

import sys

from infrastructure.models import Server


server = Server.objects.get(id=sys.argv[1])
rh = server.resource_handler.cast()
rh.init()

creds = server.get_credentials()
password = creds.get('password', None)
username = creds.get('username', None)

# the program to run must be passed separately from the arguments to that
# program
progpath = "/bin/echo"
script = "'hello remote VM'"

ret = rh.resource_technology.work_class.run_script_on_guest(
    server.resource_handler_svr_id,  # uuid
    "root",
    password,
    script,
    progpath=progpath,
    return_stdout=True
)
print ret
