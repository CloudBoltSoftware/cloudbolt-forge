winrm quickconfig -q
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
Start-Service WinRM
set-service WinRM -StartupType Automatic

(Get-WmiObject -class Win32_TSGeneralSetting -Namespace root\cimv2\terminalservices).SetUserAuthenticationRequired(0)
