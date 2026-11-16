This script will update (creating when needed) group membership and permissions
based on the user's ldap settings.

OUs will become CloudBolt groups, membership on special ldap groups:
CB-Requestors, CB-Approvers, CB-GroupManagers and CB-ResourceManagers will
dictate the permissions users will get on the CloudBolt group that matches the
user's current OU.

See the [CloudBolt docs](https://docs.cloudbolt.io/docs/cmp/configure/access-and-security/groups-roles-permissions/permission-sync/) for more information on User Permission Synchronization with AD.
