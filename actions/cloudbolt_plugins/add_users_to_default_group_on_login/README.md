This plugin adds any user logging in to a default group (line 9). This can be used to facilitate automatic assignment of new users to a default group so they can request servers from their first use.

In this instance, the users are assigned Requestor and Approver permissions on the group, and the Viewer permission is removed. This enables users to request and manage their own servers without being able to see others in the group.

This plugin should be used as part of the **Other | External Users Sync** orchestration hook.
