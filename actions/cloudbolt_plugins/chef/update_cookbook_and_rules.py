"""
Discover/Import all available cookbooks and roles into Chef

This plugin assumes a single Chef connection and should be 
ran as a Recurring Job 
"""
from common.methods import set_progress
from connectors.chef.models import ChefConf, ChefCookbook, ChefRole

def run(job, *args, **kwargs):
    # get chef connection
    chef = ChefConf.objects.get()
    
    # get current cookbooks
    cookbooks = chef.chefcookbook_set.all()
    set_progress("Found {} Imported Cookbook(s)".format(cookbooks.count()))
    
    # get current roles
    roles = chef.get_available_apps()
    set_progress("Found {} Imported Role(s)".format(roles.count()))    
    
    # discover/import all available cookbooks
    available_cookbooks = chef.discover_connector_cookbooks()
    chef.import_cookbooks_by_name(available_cookbooks)
    set_progress("Imported {} available Cookbook(s).".format(len(available_cookbooks)))    

    # discover/import all available roles
    available_roles = chef.discover_connector_roles()
    chef.import_roles_by_name(available_roles)
    set_progress("Imported {} available Role(s).".format(len(available_roles)))    
    
    if True:
        return "SUCCESS", "Complete!", ""
    else:
        return "FAILURE", "Something isn't quite right.", "Failure!"
