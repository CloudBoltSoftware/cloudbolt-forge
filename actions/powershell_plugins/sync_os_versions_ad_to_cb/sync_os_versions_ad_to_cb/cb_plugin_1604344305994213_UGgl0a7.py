$ErrorActionPreference = "Stop"

Write-Host "Running the PowerShell Plug-in code"

$cb_api_url = "{{ cb_api_url }}"
$token = "{{ plugin_api_token }}"
$headers = @{
  'Authorization' = "Bearer " + $token
}

{% for server in servers %}
    Write-Host "Getting OS version info from AD for {{ server.hostname }}"
    $adcomputer = Get-ADComputer -Identity "{{ server.hostname }}" -Properties OperatingSystem, OperatingSystemServicePack, OperatingSystemVersion
    
    $body = @{
        parameters = @{ 
            os_version = $adcomputer.OperatingSystem
            }
    }
    $json_payload = $body | ConvertTo-Json
    Write-Host "Setting the os_version parameter on '{{ server.hostname }}' to " $body.parameters.os_version
    Invoke-RestMethod -Method Post -Uri $cb_api_url"/api/v2/servers/{{ server.id }}/parameters/" -Headers $headers -Body $json_payload -ContentType 'application/json'
{% endfor %}
    
Write-Host "Fetching a list of environments from API v3"
$environments = Invoke-RestMethod -Uri $cb_api_url"/api/v3/cmp/environments/" -Headers $headers