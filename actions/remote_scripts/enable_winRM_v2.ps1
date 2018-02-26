winrm quickconfig -q
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
Start-Service WinRM
set-service WinRM -StartupType Automatic

$result = (Get-WmiObject -class Win32_TSGeneralSetting -Namespace root\cimv2\terminalservices)
if ($result) {
  $result.SetUserAuthenticationRequired(0)
}
