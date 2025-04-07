#!/usr/bin/env python

# this is a script that will power ON/OFF all active servers in one or more  resource handlers

import os
import sys
import getopt

cloudbolt_rootdir = "/opt/cloudbolt"
sys.path.insert(0, cloudbolt_rootdir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

if __name__ == '__main__':
    import django
    django.setup()

from resourcehandlers.models import ResourceHandler


def die(errcode=5):
    sys.exit(errcode)


def spew(msg, error=False):
    " Logging function. "
    if error:
        msg = '[[ERROR]]>%s' % (msg)
    print msg


def usage(msg=""):
    spew(msg="""
Arguments:
    -r or --resource_handler=
       comma delimited list of resource_handler by name

    -a or --action=
      power action to be performed [POWEROFF, POWERON]

    -h or --help
      this message

Example:
%s -r "AWS Handler" -a POWEROFF

%s
""" % (sys.argv[0], msg))


argv = sys.argv[1:]
shortOptions = "hr:a:"
longOptions = [
    "reource_handler=",
    "action=",
    "help"]

try:
    opts, rest = getopt.getopt(argv, shortOptions, longOptions)
except getopt.error as errorStr:
    spew(msg="%s" % (errorStr), error=True)
    usage()
    sys.exit(2)

environment = None
action = None

for opt, arg in opts:
    if opt in ("-h", "--help"):
        usage()
        sys.exit(0)
    if opt in ("--resource_handler", "-r"):
        res_handlers = arg
    if opt in ("--action", "-a"):
        action = arg
        if action not in ["POWEROFF", "POWERON"]:
            fmsg = """
--action or -a arguments needs to be either "POWEROFF" or "POWERON"

    You supplied: %s
""" % (arg)

            spew(msg=fmsg, error=True)
            die()


if not res_handlers or not action:
    usage('You supplied: %s , %s' % (opts, rest))
    die()

spew(msg="Resource Handlers: %s" % (environment))
spew(msg="Action: %s" % (action))


for rh_name in res_handlers.split(","):
    rh = ResourceHandler.objects.get(name=rh_name)
    if not rh:
        spew(msg="Could not find a Resource Handler with name '%s'" % (rh_name), error=True)
        die()
    active_servers = rh.server_set.filter(status='ACTIVE')
    spew(msg="Running action '%s' in %d active servers found" % (action, len(active_servers)))

    errors = 0
    for server in active_servers:
        if action == "POWEROFF" and server.power_status != action:
            result = server.power_off()
        else:
            result = server.power_on()
        if result is False:
            spew(msg="Failed to power off server '%s'." % (server.hostname))
            errors += 1

    if errors > 0:
        spew(msg="Failed to perform action %s on %d servers" % (action, errors), error=True)
        die()
    else:
        spew(msg="Success")
