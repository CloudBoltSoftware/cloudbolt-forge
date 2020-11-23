TEST_SERVER_CONNECTION = """
Write-Output "Hello World"
"""
INSTALL_WINDOWS_AGENT = """
# Load SwisPowerShell
Import-Module SwisPowerShell

# connect to SWIS
$username = "{{ connection_info.username }}"
$password = "{{ connection_info.password }}"
$swis = Connect-Swis -Username $username -Password $password

$engineId = 1
$agentName = "{{ server.hostname }}"
$hostname = "{{ server.hostname }}"
$ip = "{{ server.ip }}"
$machineUsername = "{{ server.username }}"
$machinePassword = "{{ server.password }}"

Invoke-SwisVerb $swis Orion.AgentManagement.Agent Deploy @($engineId, $agentName, $hostname, $ip, $machineUsername, $machinePassword)
"""

CENTOS = """
if [ "`id -u`" = "0" ]; then ESH='sh'; export SWR=''; else ESH='su'; export SWR='switch to root and '; echo "You will be prompted for root password."; fi; ${ESH} -c 'D=centos-5;P=/Orion/AgentManagement/LinuxPackageRepository.ashx?path=;U="http://{{ connection_info.ip }}:8787 http://cbsolawinds-sms:8787";L=/etc/yum.repos.d;M=${L}/swiagent-${D}.mirrors;mkdir -p ${L};for u in ${U};do echo "${u}${P}/dists/${D}/\$basearch";done>$M;printf "[swiagent]\nname=SolarWinds Agent\nmirrorlist=file://%s\nenabled=1\ngpgcheck=0\n" $M>${L}/swiagent-${D}.repo; echo "Repository for SolarWinds agent was added. To install agent ${SWR}use following commands:"; echo "  yum clean all && yum install swiagent"'
yum clean all && yum install swiagent -y
touch input.txt
echo "
2
{{ connection_info.ip }}
3
17778
4
{{ connection_info.username }}
5
{{ connection_info.password }}
7
\n
" > input.txt
service swiagentd init < input.txt
"""

RED_HAT = """
if [ "`id -u`" = "0" ]; then ESH='sh'; export SWR=''; else ESH='su'; export SWR='switch to root and '; echo "You will be prompted for root password."; fi; ${ESH} -c 'D=rhel-5;P=/Orion/AgentManagement/LinuxPackageRepository.ashx?path=;U="http://{{ connection_info.ip }}:8787 http://cbsolawinds-sms:8787";L=/etc/yum.repos.d;M=${L}/swiagent-${D}.mirrors;mkdir -p ${L};for u in ${U};do echo "${u}${P}/dists/${D}/\$basearch";done>$M;printf "[swiagent]\nname=SolarWinds Agent\nmirrorlist=file://%s\nenabled=1\ngpgcheck=0\n" $M>${L}/swiagent-${D}.repo; echo "Repository for SolarWinds agent was added. To install agent ${SWR}use following commands:"; echo "  yum clean all && yum install swiagent"'
yum clean all && yum install swiagent -y
touch input.txt
echo "
2
{{ connection_info.ip }}
3
17778
4
{{ connection_info.username }}
5
{{ connection_info.password }}
7
\n
" > input.txt
service swiagentd init < input.txt
"""

UBUNTU = """
bash -c 'D=ubuntu-14;P=/Orion/AgentManagement/LinuxPackageRepository.ashx?path=; dt(){ DTA=(wget curl);A=(--tries=1\ --no-check-certificate\ --read-timeout=30\ -O --insecure\ --retry\ 1\ -o); for((i=0;i<${#DTA[@]};i++));do which ${DTA[$i]}&>/dev/null&&export DT="${DTA[$i]} ${A[$i]}"&&return;done;>&2 echo "Cannot find any download tool (${DTA[*]}). Alternative URLs cannot be checked so all of them will be left enabled.";export DT=true;};dt;x(){ U=(http://{{ connection_info.ip }}:8787 http://cbsolawinds-sms:8787);for u in ${U[*]};do >&2 echo -n "Checking $u "; if ${DT} /dev/null $u/ &>/dev/null;then >&2 echo "O.K."; else echo -n "# "; >&2 echo "unreachable";fi;echo "deb ${u}${P} ${D} swiagent";done;};export X=$(x);if [ -z "$X" ]; then echo Cannot find accessible URL; exit 1; fi; echo -n "URL check finished, installing repository."; if [ "$(id -u)" = "0" ]; then ESH="bash"; SWR=""; echo; else ESH="su"; SWR="switch to root and "; echo " You will prompted for root password."; fi; ${ESH} -c "echo \"$X\" > /etc/apt/sources.list.d/swiagent-${D}.list; echo \"Repository for SolarWinds agent was added. To install agent ${SWR}use following commands:\"; echo \"  apt-get update; apt-get install swiagent\""'
apt-get update; apt-get install swiagent -y
touch input.txt
echo "
2
{{ connection_info.ip }}
3
17778
4
{{ connection_info.username }}
5
{{ connection_info.password }}
7
\n
" > input.txt
service swiagentd init < input.txt
"""
