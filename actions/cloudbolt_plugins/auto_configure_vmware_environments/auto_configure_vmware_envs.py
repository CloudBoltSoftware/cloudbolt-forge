"""
To create nearly identical environments, the clone button can be used on the
source environment's details page. However, CB admins may want some other
programmatic configuration of the environent done, like removing the expiration
date if it is a "prod" environment, or automatically setting the cluster.

This example copies all custom field (AKA parameter) and preconfig settings, and
then removes the expiration date parameter if the env name contains "Prod" (case
insensitive).
"""

from common.methods import set_progress
from infrastructure.models import CustomField, Environment

TEMPLATE_ENV_NAME = "{{environment}}"


def copy_env_parameter_settings(src_env, dst_env):
    dst_env.custom_fields = src_env.custom_fields.all()
    dst_env.custom_field_options = src_env.custom_field_options.all()

    dst_env.preconfigurations = src_env.preconfigurations.all()
    dst_env.preconfiguration_options = src_env.preconfiguration_options.all()

    # Constraints are stored in CFMs
    from behavior_mapping.models import CustomFieldMapping
    old_constraints = CustomFieldMapping.constraints.filter(
        environment=src_env, group=None)
    for old_cfm in old_constraints:
        CustomFieldMapping.constraints.create(
            custom_field=old_cfm.custom_field,
            environment=dst_env,
            group=None,
            required=old_cfm.required,
            maximum=old_cfm.maximum,
            minimum=old_cfm.minimum,
            regex_constraint=old_cfm.regex_constraint)


def run(job, *args, **kwargs):
    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))
    environment = kwargs.get('environment')
    template_env = Environment.objects.filter(name=TEMPLATE_ENV_NAME).first()
    if not template_env:
        set_progress(f"Template environment named '{TEMPLATE_ENV_NAME}' not found. Skipping copying parameter options from that environment.")
    else:
        copy_env_parameter_settings(template_env, environment)

    if "prod" in environment.name.lower():
        # This will not remove parameter constraints, but they will be ignored
        environment.clear_cfv("expiration_date")
