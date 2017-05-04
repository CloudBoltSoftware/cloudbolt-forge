winrm quickconfig -q
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
Start-Service WinRM
set-service WinRM -StartupType Automatic
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled false
