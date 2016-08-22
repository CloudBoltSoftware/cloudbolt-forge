from common.methods import set_progress
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from azure import *
from azure.servicemanagement import *

def run(job, logger=None, **kwargs):
	
    # PREREQUISITE: Must Create Custom Fields Under Infrastructure -> CustomField For Each Customfield Object
    # Any references to a template variable will be automatically created ion custom fields for you.

    # Example: FinalName = CustomField.objects.get(label='Azure Website Name')
    # You Would Create A Custom Field In The DB With The Label "Azure Website Name"

    #THIS PLUGIN ASSUMES YOU ARE DEPLOYING THIS SERVICE FOR A HOSTED WEBSITE WITH AZURE
    #This will be expanded over time to include all service tiers and configurations.

    #Define Service Variables
    subscription_id = 'YOUR-AZURE-SUBSCRIPTION-ID'

    # This key file is typically created when you first create your Azure
    # resource handler.
    certificate_path = '/var/opt/cloudbolt/resourcehandlers/azure/azureclient.pem'

    #Init Website Management Service
    set_progress("Connecting To Azure Management Service...")
    wms = WebsiteManagementService(subscription_id, certificate_path)
    set_progress("Successfully Connected To Azure Management Service!")

    #Define Azure Webspace
    Azure_Webspace = 'westuswebspace'

    #Define Azure Website Name
    Azure_Name = '{{ Azure_Website_Name }}'
    set_progress("Setting Azure Website Name To: " + Azure_Name)

    #Define Azure Website Host Names
    Azure_Hostnames = ['{}.azurewebsites.net'.format(Azure_Name)]
    set_progress("Setting Azure Hostname To " + '{{ Azure_Website_Name }}.azurewebsites.net')
    Azure_URL = Azure_Hostnames[0]
    set_progress("Setting Azure Website URL To " + Azure_URL)

    #Define Azure Website Plan
    Azure_Plan = 'VirtualDedicatedPlan'

    #Define Azure Compute Mode
    Azure_Compute_Mode = 'Shared'

    #Define Azure Server Farm
    Azure_Server_Farm='None'

    #Define Azure Site Mode
    Azure_Site_Mode='Basic'

    #Define Azure Location
    Azure_Location = 'West US'

    #Create The Service
    try:
        set_progress("Creating New Azure Website...")
        siteinfo = wms.create_site(Azure_Webspace, Azure_Name, Azure_Location, Azure_Hostnames, Azure_Plan, Azure_Compute_Mode, Azure_Server_Farm, Azure_Site_Mode)
        set_progress("Successfully Created New Azure Website!")
    except:
        set_progress("Failed to Provision Website! Please Try Again!")

    #Retrieve Publish Profile XML
    try:
        set_progress("Retrieving Website Publishing Profile")
        PublishProfileXML = wms.get_publish_profile_xml(Azure_Webspace, Azure_Name)
        Azure_Publish_Profile = PublishProfileXML.encode('ascii', 'ignore')
        set_progress("Sucessfully Retrieved Website Publishing Profile!")
    except:
        set_progress("Failed To Retrieve Website Publishing Profile!")
        FailedMessage = 'Failed To Retrieve Website Publishing Profile!'
        FailedName = CustomField.objects.get(label='Azure Publish Profile XML')
        FailedNameCV = CustomFieldValue(field=FailedName, value=FailedMessage)
        FailedNameCV.save()
        service.attributes.add(FailedNameCV)        

    #Get The Service
    services = job.parent_job.service_set.all()
    service = services[0]

    #Bind The Service Values And Save Them To A CFV (Custom Field Value)
    set_progress("Updating Azure Website URL Information To: " + Azure_URL)
    FinalURL = CustomField.objects.get(label='Azure Website URL')
    FinalURLCV = CustomFieldValue(field=FinalURL, value=Azure_URL)
    FinalURLCV.save()
    service.attributes.add(FinalURLCV)

    set_progress("Updating Azure Webspace Information To: " + Azure_Webspace)
    FinalWebspace = CustomField.objects.get(label='Azure Webspace')
    FinalWebspaceCV = CustomFieldValue(field=FinalWebspace, value=Azure_Webspace)
    FinalWebspaceCV.save()
    service.attributes.add(FinalWebspaceCV)

    set_progress("Updating Azure Location Information To: " + Azure_Location)
    FinalLocation = CustomField.objects.get(label='Azure Website Location')
    FinalLocationCV = CustomFieldValue(field=FinalLocation, value=Azure_Location)
    FinalLocationCV.save()
    service.attributes.add(FinalLocationCV)

    set_progress("Updating Hostnames Information To: " + Azure_Hostnames[0])
    FinalHostnames = CustomField.objects.get(label='Azure Website Hostname')
    FinalHostnamesCV = CustomFieldValue(field=FinalHostnames, value=Azure_Hostnames[0])
    FinalHostnamesCV.save()
    service.attributes.add(FinalHostnamesCV)

    set_progress("Updating Azure Publishing Profile Information")
    PublishProfile = CustomField.objects.get(label='Azure Publish Profile XML')
    PublishProfileCV = CustomFieldValue(field=PublishProfile, value=Azure_Publish_Profile)
    PublishProfileCV.save()
    service.attributes.add(PublishProfileCV)

    #Check The State Of The Job And Output The Result To The Console 
    success = True
    if success:
        set_progress("Successfully Deployed Azure Website Service")
        return "", "", ""
    else:
        set_progress("Failed To Deploy Azure Website Service")
        return "FAILURE", "Failed To Deploy Azure Website Service", ""
