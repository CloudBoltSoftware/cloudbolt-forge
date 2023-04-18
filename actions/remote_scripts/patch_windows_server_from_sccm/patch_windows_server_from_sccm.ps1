# This PowerShell remote script runs on the Windows Server being patched, but connects to the 
# SCCM server to fetch its software updates.
# This can be used as a Server Action (which appears as a button/drop-down option on the server list & details pages),
# within a Blueprint, as a recurring job, as a post-provision Orchestration Action, or anywhere else in CloudBolt
# that actions can be used.
# The sccm_server and site_code inputs can be provided by the user at run time or set by the admin who configures this
# action to run at a particular trigger point.

# This script was written by ChatGPT then adapted by Mike Bombard. Thanks AI and Mike.


# Define the SCCM server and site code
$SCCMServer = "{{sccm_server}}"
$SiteCode = "{{site_code}}"

# Define the Software Updates Deployment ID for the All Software Updates deployment
$DeploymentID = "GUID"

# Connect to the SCCM server
$SCCMConnection = Connect-CMServer -Server $SCCMServer -SiteCode $SiteCode

# Get all available software updates
$SoftwareUpdates = Get-CMSoftwareUpdate -DeploymentID $DeploymentID -FastLoad

# Install all available software updates
ForEach ($Update in $SoftwareUpdates)
{
    Write-Host "Installing $($Update.LocalizedDisplayName)..."
    Invoke-CMSoftwareUpdateInstallation -SoftwareUpdate $Update
}

# Disconnect from the SCCM server
Disconnect-CMServer -Connection $SCCMConnection
