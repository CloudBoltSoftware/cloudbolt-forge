# Puppet v.2.8 Agent Install

This remote script is for RHEL/CentOS and will install the puppet agent via yum assuming your template/base OS image has access to the EPEL yum repository. You'll most likely want to bind this script to the "Pre-Application Installation" orchestration action so it runs prior to associating any Puppet classes to a new server. 

## Assumptions
1. The EPEL yum repository is installed in your OS template/image.
2. The hostname of the designated Puppet Enterprise server is included in the script.
3. Autosign = True is enabled on the Puppet Enterprise server. If this is not the case, then set the waitforcert configuration to something greater than the 2m default, e.g. under the [agent] section in puppet.conf, add the line: 
 * waitforcert = 10m