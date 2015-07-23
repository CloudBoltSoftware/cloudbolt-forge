#!/bin/sh -e -x

# Example remote script, which simply restarts Apache.
#
# Only applicable to Linux servers.
# Useful to set up in CloudBolt as a Server Action so users have an easy button for
# restarting Apache.

echo "Restarting Apache"
service httpd restart
