DOWNLOAD_NEW_RELIC_AGENT_FOR_WINDOWS = r"""
$WebClient = New-Object System.Net.WebClient

$Is64Bit = [Environment]::Is64BitProcess
if($Is64Bit -eq 'True') {
    $URL = "https://download.newrelic.com/infrastructure_agent/windows/newrelic-infra.msi"
}else{
    $URL = "https://download.newrelic.com/infrastructure_agent/windows/386/newrelic-infra-386.msi"
}
Try 
    {
        $WebClient.DownloadFile($URL,"C:\newrelic-infra.msi")
    }
    Catch 
    {
        echo "Error occurred while trying to download the agent."
    }

"""

INSTALL_SCRIPT = r"""
Start-Process -Wait msiexec -ArgumentList '/qn /i "C:\newrelic-infra.msi" GENERATE_CONFIG=true LICENSE_KEY="{{ license_key }}"'
net start newrelic-infra
"""

INSTALL_AGENT_FOR_CENTOS = r"""
echo "license_key: {{ license_key }}" | sudo tee -a /etc/newrelic-infra.yml

release=$(python -c 'import platform; print(platform.linux_distribution()[1].split(".")[0])')

sudo curl -o /etc/yum.repos.d/newrelic-infra.repo https://download.newrelic.com/infrastructure_agent/linux/yum/el/$release/x86_64/newrelic-infra.repo

sudo yum -q makecache -y --disablerepo='*' --enablerepo='newrelic-infra'

sudo yum install newrelic-infra -y
"""

INSTALL_AGENT_FOR_UBUNTU = r"""
echo "license_key: {{ license_key }}" | sudo tee -a /etc/newrelic-infra.yml

curl https://download.newrelic.com/infrastructure_agent/gpg/newrelic-infra.gpg | sudo apt-key add -

distribution=$(python3 -c 'import platform; print(platform.dist()[-1])')

# Create the agent’s apt repo using the command for your distribution version
printf "deb [arch=amd64] http://download.newrelic.com/infrastructure_agent/linux/apt $distribution main" | sudo tee -a /etc/apt/sources.list.d/newrelic-infra.list

# Update your apt cache
sudo apt-get update

# Run the install script
sudo apt-get install newrelic-infra -y

"""
