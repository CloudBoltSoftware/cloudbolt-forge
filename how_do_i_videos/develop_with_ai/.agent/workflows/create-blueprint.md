---
description: How to create a new CloudBolt Blueprint
---

# Create a New CloudBolt Blueprint

This workflow guides you through creating the necessary plugins for a new CloudBolt Blueprint.

## Steps

1. **Identify Provider and Service**: Choose a directory structure like `<provider>/<service_name>` (e.g., `aws/s3_bucket`).
2. **Create Directory**:
   ```bash
   mkdir -p <provider>/<service_name>
   ```
3. **Create Build Plugin**:
   - Create `build_<service_name>.py`.
   - Implement `run(job, **kwargs)`.
   - Implement `generate_options_for_<field>` as needed.
4. **Create Discovery Plugin**:
   - Create `discover_<service_name>.py`.
   - Implement `discover_resources(**kwargs)`.
   - Define `RESOURCE_IDENTIFIER`.
5. **Create Day 2 Resource Actions**:
   - Create plugins like `add_config.py` or `update_settings.py`.
   - Implement `run(job, resource, **kwargs)`.
6. **Create Teardown Plugin**:
   - Create `teardown_<service_name>.py`.
   - Implement `run(job, **kwargs)`.

## Plugin Templates

### Build Action Template
```python
import ast
from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def run(job, **kwargs):
    resource = kwargs.get("resource")
    resource_name = "{{ resource_name }}"
    
    # List parameter handling (e.g. from a multi-select field)
    items = ast.literal_eval("""{{ items }}""")
    
    set_progress(f"Provisioning resource {resource_name} with items {items}...")
    # Logic goes here
    return "SUCCESS", f"Resource {resource_name} created", ""
```

### Discovery Plugin Template
```python
RESOURCE_IDENTIFIER = "my_resource_id"

def discover_resources(**kwargs):
    discovered = []
    # Logic to fetch resources from provider
    discovered.append({
        "name": "Resource Name",
        "my_resource_id": "unique-id",
        # other attributes
    })
    return discovered
```

### Day 2 Action Template
```python
def run(job, resource, **kwargs):
    # resource object is provided
    # Additional input parameters can be created by using Django Templates. 
    # Logic to update resource
    return "SUCCESS", "Action completed", ""
```

### Generated Options & Dependencies
To create a field that depends on another (e.g., `resource_group` depends on `environment`):

1. **In the Plugin**: Add a `generate_options_for_<field>` function.
```python
def generate_options_for_resource_group(control_value=None, **kwargs):
    # control_value is the value of the dependent field (e.g. env.id)
    if not control_value:
        return []
    env = Environment.objects.get(id=control_value)
    rh = env.resource_handler.cast()
    groups = rh.armresourcegroup_set.all()
    return [g.name for g in groups]
```

2. **In the UI**: Navigate to the parameter, set **Dependency Type** to "Regenerate Options", and select the **Controlling Field**.

### RBAC-Aware Environment Selection
Always filter the list of environments (`env_id`) by the user's group to maintain RBAC consistency.
```python
def generate_options_for_env_id(**kwargs):
    group_name = kwargs.get("group")
    if not group_name:
        return []
    
    group = Group.objects.get(name=group_name)
    envs = group.get_available_environments()
    
    # Filter by required technology (e.g., Azure, AWS)
    options = [(env.id, env.name) for env in envs if
               env.resource_handler.resource_technology.name == "Azure"]
    
    options.sort(key=lambda x: x[1])
    options.insert(0, ('', '--- Select an Environment ---'))
    return options
```

### Advanced Option Returns
For rich UI elements or pre-selections, return a dictionary:
```python
def get_options_list(field, **kwargs):
    options = [
        {'value': 'v1', 'label': 'Standard', 'description': 'Standard performance', 'icon': 'fa-server'},
        {'value': 'v2', 'label': 'Premium', 'description': 'High performance', 'icon': 'fa-bolt'},
    ]
    return {
        'options': options,
        'initial_value': 'v1',
        'sort': False
    }
```