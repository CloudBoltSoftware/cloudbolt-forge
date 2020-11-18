DOWNLOAD_DATA_DOG_AGENT_WINDOWS = """

    $WebClient = New-Object System.Net.WebClient
    Try 
    {
        $WebClient.DownloadFile("https://s3.amazonaws.com/ddagent-windows-stable/datadog-agent-6-latest.amd64.msi","C:\datadog.msi")
    }
    Catch 
    {
        echo "Error occurred while trying to download the agent."
    }
    
"""

INSTALL_DATADOG_AGENT_WINDOWS = """
    Start-Process -Wait msiexec -ArgumentList '/qn /i "C:\datadog.msi" APIKEY="{{ api_key }}"'
"""

INSTALL_DATADOG_AGENT_LINUX = """
DD_API_KEY="{{ api_key }}" bash -c "$(curl -L https://raw.githubusercontent.com/DataDog/datadog-agent/master/cmd/agent/install_script.sh)"
"""

CHECK_AGENT_STATUS_WINDOWS = """
    & "C:\Program Files\Datadog\Datadog Agent\embedded`\Agent.exe" status
"""

CHECK_AGENT_STATUS_LINUX = """
    service datadog-agent status
"""
