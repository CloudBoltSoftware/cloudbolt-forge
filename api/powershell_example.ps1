#Init Variables
$CloudBoltIP = "1.2.3.4" #Cloudbolt Server IP
$Environment = 1 #Get From URL By Clicking Environment Name On The Environments Page
$GroupNumber = 1 #Get From URL By Clicking Group Name On The Groups Page
$OSBuild = 1 #Get From URL By Clicking Group Name On The OSBuild Page
$RequestingUser = 1 #Get From URL By Clicking User In Admin Portal
$ApprovingUser = 1 #Get From URL By Clicking User In Admin Portal
$HostName = "Servername_Goes_Here" #ServerName

#Build Credential
$UserName = "CloudBolt_API_Username_Goes_Here"
$Password = "API_Password_Goes_Here" | ConvertTo-SecureString -asPlainText -Force
$Credential = New-Object System.Management.Automation.PSCredential($UserName,$Password)

#Ignore SSL Certs (Required To Prevent Errors For Some SSL Certs)
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

#Create An Order
try
{
	#Build The Order
	$GroupJSON = '{"group": "/api/v2/groups/' + $GroupNumber + '", "owner": "/api/v2/users/' + $RequestingUser + '"}'
	$Order_RequestURL = "https://$CloudBoltIP/api/v2/orders/"
	$Order = Invoke-RestMethod -Credential $Credential -Method POST -ContentType "application/json" -URI $Order_RequestURL -Body $GroupJSON
	
	#Retrieve The Order Number
	$OrderNumber = $Order._links.self.href.Split('/')[4]
	Write-Host "Created New Order - ID: $OrderNumber"
}
catch
{
	Write-Host "Unable To Create Order, Something Went Wrong. Error Message: $($Error[0].Exception)"
}

#Add A Server to The Order
try
{
	#For Parameters, Use The Specific Parameters Required By Your Resource Handler In Order To Provision The Server
	#I Have Provided Some Sample Parameters Below For Demonstration Purposes Only
	$UpdatedOrderJSON = @"
	{
		`"environment`": `"/api/v2/environments/$Environment`", 
		`"attributes`": {
			`"hostname`": `"$($HostName.ToLower())`"
		}, 
		`"parameters`": {
			`"Function`": `"fun`", 
			`"initial_linux_password`": `"*********`", 
			`"sc_nic_0`": `"nic_name`", 
			`"Workgroup`": `"wrk`", 
			`"node_location`": `"us-east1-c`", 
			`"node_size`": `"f1-micro`", 
			`"Datacenter_Code`": `"dc1`", 
			`"Tier`": `"Production`"
		}, 
		"os-build": "/api/v2/os-builds/$OSBuild"
	}
"@
	$UpdatedOrder_RequestURL = "https://$CloudBoltIP/api/v2/orders/$OrderNumber/prov-items/"
	$UpdatedOrder = Invoke-RestMethod -Credential $Credential -Method POST -ContentType "application/json" -URI $UpdatedOrder_RequestURL -Body $UpdatedOrderJSON
	Write-Host "Sucessfully Updated Order ID: $OrderNumber"
}
catch
{
	Write-Host "Unable To Create Order, Something went wrong. Error Message: $($Error[0].Exception)"
}

#Submit The Order
try
{
	$SubmitOrder_RequestURL = "https://$CloudBoltIP/api/v2/orders/$OrderNumber/actions/submit/"
	$SubmitOrder = Invoke-RestMethod -Credential $Credential -Method POST -URI $SubmitOrder_RequestURL
	Write-Host "Sucessfully Submitted Order ID: $OrderNumber"
}
catch
{
	Write-Host "Unable To Create Order, Something went wrong. Error Message: $($Error[0].Exception)"
}

#Approve The Order If Auto Approval Isn't Set
try
{
	$ApproveOrder_RequestURL = "https://$CloudBoltIP/api/v2/orders/$OrderNumber/actions/approve/"
	$ApproveOrder = Invoke-RestMethod -Credential $Credential -Method POST -URI $ApproveOrder_RequestURL
	Write-Host "Sucessfully Approved Order ID: $OrderNumber"
}
catch
{
	Write-Host "Unable To Approve Order, The Order May Not Require Approval Or Manual Approval Will Need To Be Completed. Error Message: $($Error[0].Exception)"
}

#Check The Order Status
$OrderStatus = "ACTIVE"
Do
{
	Write-Host "Order Still Processing..."
	Sleep 10
	
	#Go Grab The Status Of The Order
  	$Order_RequestURL = "https://$CloudBoltIP/api/v2/orders/$OrderNumber/"
  	$Order = Invoke-RestMethod -Credential $Credential -Method GET -URI $Order_RequestURL
  	$OrderStatus = $($Order.Status)
}
While ($OrderStatus -eq "ACTIVE")

#Update The User The Job Is Done
Write-Host "Order Has Been Completed And Returned The Status: $OrderStatus"
