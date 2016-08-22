# Configure NTP on RHEL/CentOS Servers

When installing certain pieces of software (ex. a Chef agent) it is required
that the server's time be fairly in sync with reality. This remote script hook
can be used at the Post-Network-Config Trigger Point in CloudBolt's
Orchestration Actions to ensure that the newly built VM can accurately tell the
time, before further software installation is attempted.

