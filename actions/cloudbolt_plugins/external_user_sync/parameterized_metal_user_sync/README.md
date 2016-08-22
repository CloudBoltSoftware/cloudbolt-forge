This external user sync CloudBolt Plugin will update (creating when needed) group membership and permissions based on the user's AD security group membership.

The script takes as action inputs the security group names, and creates 3 groups (Silver, Bronze, and Gold) to put the users into.

This Plugin can be useful for the case where you want some users in AD to have access to all groups in CB, but some users to only be a requester on certain groups.

Security groups should exist within AD for requesters that end in "-Gold", "-Bronze", and "-Silver", plus one group each for viewers, approvers, resource admins, and group admins.

See the [CloudBolt docs](http://docs.cloudbolt.io/) for more information on User Permission Synchronization with AD.
