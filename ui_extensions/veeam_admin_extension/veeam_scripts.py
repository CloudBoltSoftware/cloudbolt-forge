module = '/var/opt/cloudbolt/proserv/xui/veeam/remote_scripts/take_backup.ps1'

all_remote_scripts = [
    {
        'name': 'Take Backup',
        'description': ("An action to take a backup on a specific server"),
        'hook_point': 'server_actions',
        'enabled': True,
        'module': module,
        'hook_type': 'remote_script'
    }
]

INSTALL_WINDOWS = """
#initialize veeam powershell
Add-PSSnapin VeeamPSSnapin
#Set-NetFirewallRule -DisplayGroup "File And Printer Sharing" -Enabled True

 #create a windows server

 #get variables to create a windows server
 $Name = "{{ server.hostname }}"
 $User = "{{ server.username }}"
 $Password = "{{ server.password }}"
$Description = 'Windows Server'
#create windows login credentials
$LocalAdmin = Add-VBRCredentials -Type Windows -User $User -Password $Password -Description 'Windows local admin credentials'

#add the windows server
Add-VBRWinServer -Name $Name -Description $Description -Credentials $LocalAdmin

# Disable File And Printer Sharing
#Set-NetFirewallRule -DisplayGroup "File And Printer Sharing" -Enabled False

"""

INSTALL_LINUX = """
#initialize veeam powershell
Add-PSSnapin VeeamPSSnapin

# create a linux server
#function createLinuxServer() {
#get linux server variables
$Name = "{{ server.hostname }}"
$User = "{{ server.username }}"
$Password = "{{ server.password }}"
$SshPort = 22
$Description = "Linux server"

#create linux vm credentials
$LinuxAdministrator = Add-VBRCredentials -Type Linux -User $User -Password $Password -SshPort $SshPort

#add the linux server
Add-VBRLinux -Name $Name -Description $Description -Credentials $LinuxAdministrator

"""
CREATE_BACKUP = """
    Add-PSSnapin VeeamPSSnapin

    # Then connect to the VBR Server

    $HOST_SERVER = "{{ veeam_server.ip }}"
    $UserName = "{{ veeam_server.username }}"
    $Password = "{{ veeam_server.password }}"
    $VmName = "{{ server.hostname }}"

    Connect-VBRServer -Server $HOST_SERVER -Port 9392  -User $UserName -Password $Password

    $Random = Get-Random
    $BackUpJobName = $VmName + "Backup Job"

    # Get the VM
    $entity = Find-VBRViEntity -Name $VmName

    $repository = Get-VBRBackupRepository -Name "Local Backups"

    Add-VBRViBackupJob -Name $BackUpJobName -Entity $entity -BackupRepository $repository

    # Start The Backup Job
    Get-VBRJob -Name $BackUpJobName | Start-VBRJob

"""
CHECK_VM = """
    Add-PSSnapin VeeamPSSnapin

    # Then connect to the VBR Server

    $HOST_SERVER = "{{ veeam_server.ip }}"
    $UserName = "{{ veeam_server.username }}"
    $Password = "{{ veeam_server.password }}"
    $VmName = "{{ server.hostname }}"

    Connect-VBRServer -Server $HOST_SERVER -Port 9392  -User $UserName -Password $Password

    Find-VBRViEntity -Name $VmName

"""
RESTORE_TO_AZURE = """
    Add-PSSnapin VeeamPSSnapin

    # Then connect to the VBR Server

    $HOST_SERVER = "{{ connection_info.ip }}"
    $UserName = "{{ connection_info.username }}"
    $Password = "{{ connection_info.password }}"
    
    Connect-VBRServer -Server $HOST_SERVER -Port 9392  -User $UserName -Password $Password
    
    $restorepoint = Get-VBRBackup -Name "{{ backup_name }}" | Get-VBRRestorePoint | Select -Last 1
    $account = Get-VBRAzureAccount -Type ResourceManager | Select -Last 1
    $subscription = Get-VBRAzureSubscription -Account $account -name "Pay-as-you-go"
    $storageaccount = Get-VBRAzureStorageAccount -Subscription $subscription -Name "{{ storage_account }}"
    $location = Get-VBRAzureLocation -Subscription $subscription -Name "{{ location }}"
    $vmsize = Get-VBRAzureVMSize -Subscription $subscription -Location $location -Name "{{ vm_size}}"
    $network = Get-VBRAzureVirtualNetwork -Subscription $subscription -Name "{{ network_name }}"
    $subnet = Get-VBRAzureVirtualNetworkSubnet -Network $network
    $resourcegroup = Get-VBRAzureResourceGroup -Subscription $subscription -Name "{{ resource_group }}"
    Start-VBRVMRestoreToAzure -RestorePoint $restorepoint -VMName "{{ vmname }}" -Subscription $subscription -StorageAccount $storageaccount -VmSize $vmsize -ResourceGroup $resourcegroup -VirtualNetwork $network -VirtualSubnet $subnet

"""
RESTORE_TO_EC2 = """
    Add-PSSnapin VeeamPSSnapin

    # Then connect to the VBR Server

    $HOST_SERVER = "{{ connection_info.ip }}"
    $UserName = "{{ connection_info.username }}"
    $Password = "{{ connection_info.password }}"

    Connect-VBRServer -Server $HOST_SERVER -Port 9392  -User $UserName -Password $Password
    
    $restorepoint = Get-VBRBackup -Name "{{ backup_name }}" | Get-VBRRestorePoint | Select -Last 1
    $account = Get-VBRAmazonAccount -AccessKey "{{ amazon_access_key }}"
    $region = Get-VBRAmazonEC2Region -Account $account -RegionType "{{ region_type }}" -Name "{{ region_name }}"
    $vm_disk = Get-VBRFilesInRestorePoint -RestorePoint $restorepoint | Where FileName -Like ‘*flat.vmdk*’
    $vm_disk_name = $vm_disk.FileName
    $config = New-VBRAmazonEC2DiskConfiguration -DiskName $vm_disk_name -Include -DiskType "{{ disk_type }}"
    $instance = Get-VBRAmazonEC2InstanceType -Region $region -Name "{{ instance_type }}"
    $vpc = Get-VBRAmazonEC2VPC -Region $region -AWSObjectId "{{ vpc_id }}"
    $sgroup = Get-VBRAmazonEC2SecurityGroup -VPC $vpc -Name "{{ sgroup_name }}"
    $subnet = Get-VBRAmazonEC2Subnet -VPC $vpc -AvailabilityZone  "{{ availability_zone }}"
    
    Start-VBRVMRestoreToAmazon -RestorePoint $restorepoint -Region $region -LicenseType  "{{ license_type }}" -InstanceType $instance -VMName "{{ vm_name }}" -DiskConfiguration $config -VPC $vpc -SecurityGroup $sgroup -Subnet $subnet -Reason "{{ reason }}"
"""
GET_BACKUPS = """
 #get all backups
function getAllBackups {
    $backups = Get-VBRBackup
    foreach ($backup in $backups) {
        Write-Output('Backup Name: ' + $backup.Name + ' Creation time: ' + $backup.CreationTime)
    }
}
"""