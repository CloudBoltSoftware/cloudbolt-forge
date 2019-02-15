"""
This is a working sample CloudBolt plug-in for you to change your portals color randomly 
"""
from random import randint

from common.methods import set_progress
from portals.models import PortalConfig
from utilities.colors import rgb_to_hex

def run(*args, **kwargs):
    only_change_default_portal = "{{ only_change_default_portal }}" == "True"

    if only_change_default_portal:
        set_progress("Changing colors only for the default portal")
        # get_current_portal() is used here not to get the current user's portal (since this is
        # run in the context of an asynchronous job, there is no current portal), but instead to
        # get the default portal.
        portals = [PortalConfig.get_current_portal()]
    else:
        set_progress("Changing colors only for all portals")
        portals = PortalConfig.objects.all()

    for portal in portals:
        set_random_colors(portal)
    
    return "SUCCESS", "Portal colors changed", ""


def set_random_colors(portal):
    # Clear the "derived value fields" (things like the footer background color,
    # which is by default automatically set to the same color as the top nav bar
    # background color) so that they will be derived properly.
    for f in portal._derived_value_fields:
        setattr(portal, f, None)
        
    fields = [
        'banner_bg_color',
        'topnav_bg_color',                                                  
        'topnav_text_color',
        'content_bg_color',
        'content_text_color',                                               
        'heading_text_color',                                               
        'tooltip_bg_color',                                                 
        'tooltip_text_color',
    ]
    
    for f in fields:
        setattr(portal, f, rgb_to_hex([randint(0,255), randint(0,255), randint(0,255)]))
        set_progress("Changing {} to {}".format(f, getattr(portal, f)))
    portal.save()
