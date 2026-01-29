# CloudBolt Development Context

This file serves as a consolidated reference for all instructions recovered from the `proserv` and `shared_modules` workspaces.

## System Architecture
- **Platform**: CloudBolt CMP (Django-based Hybrid Cloud Orchestrator).
- **Customizations**: Managed in `/var/opt/cloudbolt/proserv`.
- **Shared Logic**: Reusable Python modules in `/var/www/html/cloudbolt/static/uploads/shared_modules`.
- **Typings**: Internal model definitions located via the `typings/` symlink in `proserv/`.

## Plugin Structure
All CloudBolt plugins (Actions, Discovery, Build, Teardown) must follow this basic structure:

### Entry Point
```python
def run(job, **kwargs):
    # Core logic here
    return "SUCCESS", "Message", ""
```

### Return Formats
- **3-Tuple**: `(status, output, errors)` - Traditional status format.
- **Dictionary**: `{"status": "...", "output_message": "...", "outputs": {"key": "val"}}`. The `outputs` dictionary allows passing data to subsequent steps in a workflow using `{{ outputs.step_name.key }}`.

## Plugin Parameterization
CloudBolt uses Django template syntax to auto-detect and inject input parameters.

### Declaration Syntax
Use `{{ variable_name }}` anywhere in your code. CloudBolt will scan the file and create an **Action Input** for each unique variable.

### Best Practices & Security
- **Quoting**: **CRITICAL** Always wrap variables in quotes if they are strings: `api_key = "{{ api_key }}"`. This prevents arbitrary Python injection from user input.
- **List Parameters**: For parameters that should be parsed as a list (e.g., multi-select inputs), use `ast.literal_eval` with triple-double-quotes:
  ```python
  import ast
  items = ast.literal_eval("""{{ items }}""")
  ```
  This ensures that multi-line or complex string representations are handled safely.
- **Type Casting**: Cast to the required type if the input is not a string: `port = int("{{ port }}")`.
- **Context Access**: Parameters can access execution context objects like `{{ server.hostname }}`.

## Generated Options & Dependencies
Generated Options allow you to dynamically populate parameter choices using Python logic.

### Function Naming
- **Internal to Plugin**: `generate_options_for_<field_name>(**kwargs)`.
- **Orchestration Action**: `get_options_list(field, **kwargs)`.
- **Autocomplete**: `suggest_options(field, query, **kwargs)`.

### Advanced Returns
Return a dictionary for more control in the UI:
```python
return {
    'options': [('v1', 'Label 1'), ('v2', 'Label 2')],
    'initial_value': 'v1',
    'override': True, # Bypass standard constraints
    'sort': True      # Sort options by label
}
```
Options can also be dictionaries for rich UI: `{'value': 'v1', 'label': 'L1', 'description': '...', 'icon': '...'}`.

### Parameter Dependencies
Dependencies allow fields to react to other selections.
- **`control_value`**: The value of a single controlling field.
- **`control_value_dict`**: A dictionary of values when multiple fields are controlling:
  ```python
  node_size = control_value_dict.get('node_size')
  os_build = control_value_dict.get('os_build')
  ```
- **UI Config**: Set **Dependency Type** to "Regenerate Options" in the parameter settings.

### Standard Dependency Fallback
When a field depends on another (e.g., `location` depends on `env_id`), always return a clear prompt if the controlling field is empty.
```python
def generate_options_for_location(field, control_value=None, **kwargs):
    if not control_value:
        return [('', '------ Please select an environment first ------')]
    # ... logic ...
```
This ensures the UI remains intuitive and guides the user to the correct next step.

### RBAC-Aware Environment Selection
Always filter the list of environments (`env_id`) by the user's group to maintain RBAC consistency.
```python
def generate_options_for_env_id(**kwargs):
    group_name = kwargs.get("group")
    if not group_name:
        return []
    
    group = Group.objects.get(name=group_name)
    envs = group.get_available_environments()
    
    # Filter by required technology
    options = [(env.id, env.name) for env in envs if
               env.resource_handler.resource_technology.name == "Azure"]
    
    return options
```

## Internal Model Discovery
To understand the available methods and fields for internal CloudBolt objects (like `Resource`, `Server`, `Environment`), refer to the type stubs in the `typings/` directory.

**Standard Location**: `/var/opt/cloudbolt/proserv/typings/`
- Search here to find exactly what methods are available (e.g., `resources/models.pyi` for `Resource.power_on_servers()`).
- Use these stubs as the "Source of Truth" for internal API calls.
Shared Modules act as a centralized Python package accessible by all plugins (Blueprints, UI Extensions, Orchestration Actions, etc.).

### Referencing Shared Modules
All modules in the `shared_modules` directory can be imported using the standard Python `import` syntax through the `shared_modules` package.

**Syntax:**
```python
from shared_modules.module_name import function_or_class_name
```

**Example:**
```python
from shared_modules.generated_options import generate_options_for_environment
from shared_modules.azure_connection import AzureConnection
```

### Key Features
- **Global Availability**: Automatically included in the Python path for all CloudBolt plugins.
- **Cross-Module Imports**: Shared Modules can import other Shared Modules using the same `from shared_modules import ...` syntax.
- **Modular Logic**: Ideal for API clients, common utilities, and complex "Generated Options".

### Integration Patterns
When building integrations to external systems inside Shared Modules, follow these best practices:
1. **Class-based Wrappers**: Encapsulate the external system's REST API or SDK logic in a class (e.g., `class ExternalSystem(object):`).
2. **ConnectionInfo Integration**: Use the `ConnectionInfo` model to manage URLs, ports, and credentials.
3. **Multi-Auth Support**: Implement handlers for different authentication types (BASIC, OAUTH2, Token).
4. **CloudBolt Object Mapping**: Include methods to write results or artifacts back to CloudBolt `Resource` or `Server` objects.
5. **Logging**: Use `ThreadLogger` for background execution and `common.methods.set_progress` for user-facing job progress.

### Advanced Patterns
- **Resource Handler (RH) Connectivity**: For systems with built-in CloudBolt support, use the RH object directly (e.g., `VCDHandler.objects.get(id=rh_id)`) to leverage existing credential management.
- **Async Polling**: Use the `@with_retries` decorator to poll external task/job statuses until completion.
- **Pagination**: Implement a generic `list_all_results` pattern that loops through API pages.
- **Data Translation**: Centrally handle XML-to-JSON or custom key cleanup using modules like `xmltodict`.

### UI and Helper Patterns
- **Stateless Helpers**: Use modules like `cloudbolt_shared.py` for common operations on CloudBolt objects (e.g., bulk updating custom fields).
- **Cascading Options**: Place `generate_options_for_<field>` functions in Shared Modules. Use `control_value` to support cascading UI fields (e.g., selecting an Org after selecting a Provider).
- **Empty State UI**: Always return `[("", "---No items---")]` when list results are empty to provide clear feedback in the UI.

## Core Components

### 1. Blueprints
Located in `<provider>/<service_name>/` (e.g., `aws/s3_bucket/`).
- **Build Plugin**: `run(job, **kwargs)` and `generate_options_for_<field>`.
- **Discovery Plugin**: `discover_resources(**kwargs)`
    - **Mandatory Hydration**: If the `list()` command returns "thin" objects lacking required properties (e.g., Key Vaults), you MUST call `get()` for each item to fetch its full properties.
    - **Native SDK Clients**: Use `handler.get_api_wrapper()` and `configure_arm_client(wrapper, ClientClass)` to instantiate SDK clients. There is no need for intermediate shared modules like `AzureConnection` if the SDK satisfies the requirements.
    - **Global Discovery Scope**: Discovery plugins should loop through ALL relevant Resource Handlers (e.g., `AzureARMHandler.objects.all()`) rather than just the one passed in `handler_id`. This ensures resources across all subscriptions/accounts are inventoried.
    - **Mandatory Resource Name**: Every discovered resource dictionary MUST include a `name` key for display purposes.
    - **Namespaced Discovery Properties**: All other keys in the discovery dictionary SHOULD be namespaced (e.g., `azure_key_vault_location`) to match the blueprint's namespaced parameters and custom fields. Non-namespaced keys like `location` or `sku` should be removed.
    - **Cloud-Native Identifiers**: Always prioritize using a unique ID from the cloud provider (e.g., Azure Resource ID) as the primary identifier in CMP. This ensures resources are uniquely identified even if secondary attributes (like URIs or names) are duplicated or changed.
    - **RESOURCE_IDENTIFIER**: Must be defined as the namespaced custom field holding the cloud ID (e.g., `azure_key_vault_id`).
- **Day 2 Actions**: `run(job, resource, **kwargs)`.
- **Teardown**: `run(job, **kwargs)`.
    - **Idempotent Teardown**: Teardown plugins MUST be idempotent. If metadata required for deletion (like the Azure ID) is missing, or if the resource cannot be found in the cloud (e.g., a 404 error), the plugin should return a `WARNING` status rather than a `FAILURE`. The message should state what was missing and that the system assumes the resource has already been deleted.
    - **Custom Field Retrieval**: Use `resource.get_value_for_custom_field("cf_name")` to get the casted value (STR, INT, etc.) or `resource.get_cfv_for_custom_field("cf_name").value` for the raw value object. Avoid using non-existent shorthand like `get_cfv`.

### 2. XUI (eXtended User Interface)
Located in `xui/<extension_id>/`.
- Standard Django layout: `urls.py`, `views.py`, `templates/`, `static/`.
- Many are auto-discovered by CloudBolt.

### 3. Shared Modules
Key libraries for cross-system interaction:
- `azure_connection.py`, `vcd.py`, `vmware.py`: Specialized provider connections.
- `cloudbolt_shared.py`: Common CloudBolt utilities.
- `ansible_automation.py`, `terraform.py`: Infrastructure as Code integrations.

## Development Standards
- **Language**: Python 3.x.
- **Logging**: Use `common.methods.set_progress(message)`.
- **Attributes**: Store metadata as custom fields on the `resource` object.

## Namespaced Custom Fields
When storing metadata on a CloudBolt `Resource`, always follow these rules to ensure data integrity and avoid collisions:
1. **RH ID Over Environment**: Always store the Resource Handler ID (`azure_rh_id`) instead of the Environment ID. The RH ID is the critical connection for API operations after the initial provisioning.
2. **Pre-Creation**: For **Build** and **Teardown** plugins, custom fields MUST be created using `create_custom_field` BEFORE any values are set on the resource.
3. **Discovery Auto-Creation**: For **Discovery** plugins, manual pre-creation is unnecessary. CloudBolt will automatically create any custom fields contained within the returned discovery dictionary that do not already exist.
4. **Namespacing**: Prefix field names with the service name (e.g., `azure_key_vault_`).
4. **Consistency**: Use the same names and pre-creation logic in Build, Discovery, and Teardown plugins.
5. **Metadata Minimization**: Avoid storing redundant metadata if it can be derived from the primary cloud ID (e.g., extracting Resource Group from an Azure Resource ID). This reduces data duplication and potential synchronization errors.
7. **Decoupled Naming**: Distinguish between **Action Inputs** and **Persistent Metadata**:
    - **Action Inputs** (`{{ variable }}`): Use short, descriptive names (e.g., `location`, `sku`, `resource_group`). CloudBolt automatically converts these to user-friendly titles in the UI (e.g., `resource_group` -> "Resource Group").
    - **Persistent Metadata** (Custom Fields): Use namespaced names (e.g., `azure_key_vault_location`) for storage on the `Resource` object to avoid collisions and ensure data integrity.
8. **Parameter Consistency**: While Action Inputs are short, the mapping in the Blueprint UI should link discovery results (namespaced) to these short parameters. Ensure the same data is consistently represented across all plugins, even if the key names differ between the UI and storage layers.

Example:
```python
from c2_wrapper import create_custom_field

def create_custom_fields():
    create_custom_field("azure_service_attr", "Human Label", "STR")

def run(job, resource, **kwargs):
    create_custom_fields()
    resource.set_value_for_custom_field("azure_service_attr", "Value")
```

## Global Settings
Located in `customer_settings.py`.

## Workflows
- `/create-blueprint`: Scaffolds the 4-part plugin structure for new services.
- `/create-xui`: Scaffolds a new Django-based UI extension.
