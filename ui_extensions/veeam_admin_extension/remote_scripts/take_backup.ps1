
    # Create a backup
    $HOST_SERVER = "10.55.62.189"
    echo $HOST_SERVER
    Import-Module -Name Microsoft.PowerShell.Management
    Get-PSSnapin -Registered
    Add-PSSnapin VeeamPSSnapin
    
    # Then connect to the VBR Server
    
    $HOST_SERVER = "10.55.62.189"
    $UserName = "Administrator"
    $Password = "CloudBolt!"
    $VmName = "Veeam-server-test"
    
    Connect-VBRServer -Server $HOST_SERVER -Port 9392  -User $UserName -Password $Password
    
    $Random = Get-Random
    $BackUpJobName = $VmName + "Backup Job"
    
    # Get the VM
    $entity = Find-VBRViEntity -Name $VmName 
    
    $repository = Get-VBRBackupRepository -Name "Local Backups"
    
    Add-VBRViBackupJob -Name $BackUpJobName -Entity $entity -BackupRepository $repository
    
    # Start The Backup Job
    Get-VBRJob -Name $BackUpJobName | Start-VBRJob

