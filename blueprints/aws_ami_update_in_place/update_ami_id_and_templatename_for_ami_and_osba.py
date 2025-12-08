"""
This plug-in updates existing Amazon Machine Image (AMI) records in CloudBolt by
replacing an old AMI ID with a new one and updating the associated template
name across both AmazonMachineImage and OSBuildAttribute models.

Workflow:
1. User selects an OSBuild value.  
   → NOTE: The `osbuild` parameter **must act as a control field**, and any
     parameters depending on it (such as old_ami_id and region) must be
     configured with CloudBolt’s *regenerate_on_change* dependency so that their
     option lists refresh dynamically.

2. Based on the selected OSBuild:
   - `old_ami_id` list is dynamically generated.
   - After an AMI is selected, the available AWS regions are dynamically generated.

3. When executed, the script:
   - Locates AMIs that match the selected old AMI ID.
   - Updates each AMI's `ami_id` and `templatename`.
   - Updates the related OSBuildAttribute template name.

This ensures OSBuild-specific AMIs are updated cleanly and consistently.
"""

from common.methods import set_progress
from externalcontent.models import OSBuild, OSBuildAttribute
from resourcehandlers.aws.models import AmazonMachineImage

import logging

logger = logging.getLogger("AWS")

# Initial parameter values — printed to progress for visibility
old_ami_id = "{{old_ami_id}}"
set_progress(f"Old AMI ID: {old_ami_id}")

region = "{{region}}"
set_progress(f"Region: {region}")

osbuild = "{{osbuild}}"
set_progress(f"OSBuild: {osbuild}")

new_template_name = "{{new_template_name}}"
set_progress(f"New template name: {new_template_name}")

new_ami_id = "{{new_ami_id}}"
set_progress(f"New AMI ID: {new_ami_id}")


def run(job, *args, **kwargs):
    """
    Updates all AMIs matching old_ami_id:
      - Replaces the AMI ID with new_ami_id
      - Updates the template name
      - Updates the associated OSBuildAttribute template name
    """
    set_progress("Fetching AMIs to update...")
    amis = AmazonMachineImage.objects.filter(ami_id=old_ami_id)
    set_progress(f"Found {amis.count()} AMIs with old AMI ID {old_ami_id}")

    for ami in amis:
        set_progress("########################")
        set_progress(f"Updating AMI {ami.ami_id} template name to {new_template_name}")

        # Update AMI details
        ami.ami_id = new_ami_id
        ami.templatename = new_template_name
        ami.save()
        set_progress(f"AMI {new_ami_id}, {ami.ami_id} template name updated")

        set_progress("########################")
        # Update OSBuildAttribute reference
        osba = ami.osbuildattribute_ptr
        set_progress(f"Updating OSBuildAttribute template name for AMI {ami.ami_id}")
        osba.template_name = new_template_name
        osba.save()
        set_progress(f"OSBuildAttribute for AMI {ami.ami_id} updated")


def generate_options_for_osbuild(field, **kwargs):
    """
    Generates a list of OSBuild options.
    NOTE: This parameter should be set as a control field because
    dependent parameters rely on its value to regenerate their options.
    """
    osbs = OSBuild.objects.filter(
        environments__resource_handler__awshandler__isnull=False
    ).distinct()

    options = [(osb.id, osb.name) for osb in osbs]

    return {"options": options, "override": True, "sort": True}


def generate_options_for_old_ami_id(
    field, control_value=None, control_value_dict=None, **kwargs
):
    """
    Generates a list of old AMI IDs based on the selected OSBuild.
    This function requires:
      - `osbuild` to be the control_value
      - The "old_ami_id" parameter to have regenerate_on_change pointing to "osbuild"
    """
    options = []

    if not control_value:
        return {"options": options}

    try:
        # control_value is OSBuild id or global_id
        osbuild = control_value

        amis = (
            AmazonMachineImage.objects.filter(os_build=osbuild)
            .values_list("ami_id", flat=True)
            .distinct()
        )

        options = [(ami, ami) for ami in amis]

    except OSBuild.DoesNotExist:
        logger.warning(f"OSBuild not found for value: {control_value}")

    return {"options": options, "override": True, "sort": True}


def generate_options_for_region(
    field, control_value=None, control_value_dict=None, **kwargs
):
    """
    Generates AWS regions based on the chosen AMI ID.
    Requires:
      - `old_ami_id` to be configured as a control_value
      - The "region" parameter to regenerate_on_change on "old_ami_id"
    """
    options = []

    if not control_value:
        return {"options": options}

    try:
        ami_id = control_value
        logger.info(f"Control_value: {control_value}")

        amis = AmazonMachineImage.objects.filter(ami_id=ami_id)

        # Collect distinct regions
        regions = {ami.region for ami in amis if ami.region}

        options = [(r, r) for r in sorted(regions)]

    except OSBuild.DoesNotExist:
        logger.warning(f"OSBuild not found for value: {control_value}")

    return {"options": options, "override": True, "sort": True}
