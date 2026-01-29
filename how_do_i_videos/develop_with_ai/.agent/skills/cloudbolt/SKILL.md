---
name: CloudBolt Development
description: Instructions and context for developing plugins and extensions for the CloudBolt CMP.
---

# CloudBolt Development Skill

This skill provides context for working with the CloudBolt Cloud Management Platform (CMP).

## Architecture Overview
CloudBolt is a Python-based platform (Django) used for hybrid cloud orchestration. The codebase in this repository represents "Professional Services" (proserv) customizations.

### Core Components
- **XUI (eXtended User Interface)**: Django-based UI extensions located in `xui/`.
- **Blueprints**: Logical packages of content that define how to build, discover, manage (Day 2), and teardown resources. Often organized by provider/service (e.g., `azure/web_app`).
- **CloudBolt Actions / Plugins**: Python modules run within the CloudBolt environment.
- **Remote Scripts**: Bash, PowerShell, etc., scripts run on remote hosts.

### Blueprint Components
A complete blueprint typically includes:
- **Build Actions**: Scripts that handle the initial provisioning.
    - Entry point: `run(job, **kwargs)`.
    - Often includes `generate_options_for_<field>` for dynamic UI fields.
- **Discovery Plugins**: Scripts that inventory existing resources.
    - Entry point: `discover_resources(**kwargs)`.
    - Returns a list of dictionaries with resource attributes.
    - Defines `RESOURCE_IDENTIFIER`.
- **Day 2 Resource Actions**: Scripts for ongoing management tasks.
    - Entry point: `run(job, resource, **kwargs)`.
- **Teardown Actions**: Scripts that handle resource deletion.
    - Entry point: `run(job, **kwargs)`.

## Plugin Parameterization
- **Syntax**: Use `{{ variable_name }}` to declare input parameters.
- **Auto-Discovery**: CloudBolt creates UI fields for all `{{ }}` variables.
- **Security**: **Always** wrap variables in quotes: `auth_token = "{{ auth_token }}"`.
- **List Parameters**: Use `ast.literal_eval("""{{ var }}""")` for list/object inputs.
- **Generated Options**: Use `generate_options_for_<field>(**kwargs)` or `get_options_list`.
- **Dependencies**: Use `control_value` (single) or `control_value_dict` (multiple) for dependent fields.
- **RBAC**: Always filter environment lists (`env_id`) using `group.get_available_environments()`.
- **Typing**: Cast variables in code: `count = int("{{ count }}")`.

## Development Standards
- **Python**: Use Python 3.x.
- **CloudBolt API**: Use `common.methods.set_progress` for logging.
- **Resource Management**: Store resource-specific metadata as custom fields on the `resource` object.
- **Proserv Structure**:
    - XUI extensions reside in `xui/<extension_id>/`.
    - Blueprint plugins reside in functional directories like `azure/<blueprint_name>/`.

## Key Directories
- `/var/opt/cloudbolt/proserv/xui/`: XUI extensions.
- `/var/opt/cloudbolt/proserv/<provider>/<service>/`: Blueprint-related plugins.
- `/var/opt/cloudbolt/proserv/customer_settings.py`: Global overrides.
- `/var/opt/cloudbolt/proserv/typings/`: Type stubs for internal CloudBolt models (Source of Truth for methods/fields).
- `/var/www/html/cloudbolt/static/uploads/shared_modules/`: Globally accessible shared logic.

## Shared Modules Usage
Shared Modules are available in CloudBolt 2023.5+ and are imported using:
```python
from shared_modules.module_name import item
```

### Integration Best Practices
- **Class-based**: Wrap API logic in classes for reusability.
- **ConnectionInfo / RH**: Use `ConnectionInfo` or `ResourceHandler` objects for config.
- **Mapping**: Implement methods to sync external state back to CloudBolt `Resource` objects.
- **Async Polling**: Use `@utilities.decorators.with_retries` for external tasks.
- **Cascading UI**: Use `control_value` in `generate_options_for_*` for linked fields.
- **Logging**: Use `utilities.logger.ThreadLogger` for logging that isn't user facing and `common.methods.set_progress` for information that should be surfaced to a self-service user. 

## Common Tasks
- **Creating a new XUI**: Scaffold a new directory in `xui/` with `urls.py`, `views.py`, and a `README.md`.
- **Modifying Settings**: Update `customer_settings.py` to enable/disable features.
