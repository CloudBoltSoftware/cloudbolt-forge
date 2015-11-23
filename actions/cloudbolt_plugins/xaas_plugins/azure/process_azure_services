#!/usr/local/bin/python2.7
from common.methods import set_progress
from infrastructure.models import CustomField
from orders.models import CustomFieldValue
from azure import *
from azure.servicemanagement import *

def run(job, **kwargs):

    # Place this pluign in the Orchestration Actions -> Other -> Pre-Job hook
    # This script will allow you to hook into any buildup or teardown for any Azure services found.
    # This hook is called when the 'Delete' button on a service is pressed.
    # This script currently only supports Azure Websites.

    if job.type == "orchestration_hook":
        action = job.job_parameters.cast().hook
        if action.name == "Delete Service":

            # Evaluate Service To See If There Is A Custom Defined Teardown Process
            for service in job.service_set.all():
                set_progress("Evaluating XaaS tear-down needs for '{}'".format(service))
                if service.attributes.filter(field__name="Azure_Publish_Profile_XML").exists():

                    #########################Teardown Azure Websites#########################
                    set_progress("Azure Website Found! Tearing Down Website")

                    #Define Service Variables
                    subscription_id = '3ba523b7-5b38-430c-9ae7-b89b6051f756'
                    certificate_path = '/var/opt/cloudbolt/resourcehandlers/azure/azureclient.pem'

                    #Init Website Management Service
                    set_progress("Connecting To Azure Management Service...")
                    wms = WebsiteManagementService(subscription_id, certificate_path)
                    set_progress("Successfully Connected To Azure Management Service!")

                    #Get Service Field - Azure Webspace
                    set_progress("Retrieving Service Field - Azure Webspace")
                    Azure_Webspace = service.attributes.filter(field__label="Azure Webspace")[0].value
                    set_progress("Found Azure Webspace: {}".format(Azure_Webspace))

                    #Get Service Field - Define Azure Website Name
                    set_progress("Retrieving Service Field - Azure Website")
                    Azure_Name = service.attributes.filter(field__label="Azure Website Name")[0].value
                    set_progress("Found Azure Website: {}".format(Azure_Name))

                    #Delete Website
                    try:
                        set_progress("Deleting Azure Website...")
                        deletedwebsite = wms.delete_site(Azure_Webspace, Azure_Name, delete_empty_server_farm=False, delete_metrics=True)
                        set_progress("Successfully Deleted Azure Website - {0}".format(Azure_Name))
                    except:
                        set_progress("Site Deletion Failed! Please Try Again!")
                    #########################Teardown Azure Websites#########################

                else:
                    set_progress("This Service Is Not An Azure Service, Azure Service Teardown Process Skipped.")

    return "", "", ""
