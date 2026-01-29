---
description: How to create a new CloudBolt Shared Module for external integrations
---

# Create a New Shared Module

This workflow guides you through creating a new Shared Module for external system integrations.

## Steps

1. **Choose a Name**: Select a unique, lowercase name (e.g., `my_system.py`).
2. **Create File**:
   ```bash
   touch /var/www/html/cloudbolt/static/uploads/shared_modules/<name>.py
   ```
3. **Define Integration Class**:
   - Use `ConnectionInfo` for authentication.
   - Implement common HTTP methods (`get`, `post`, etc.).
   - Add logic for waiting on asynchronous jobs if applicable.
4. **Implement Object Mapping**:
   - Add methods to write artifacts back to CloudBolt `Resource` custom fields.

## Template: Integration Module

```python
from utilities.models import ConnectionInfo
from resources.models import Resource
from common.methods import set_progress
from utilities.logger import ThreadLogger
import requests

logger = ThreadLogger(__name__)

class MyIntegration(object):
    def __init__(self, conn_info_id):
        self.conn_info = ConnectionInfo.objects.get(id=conn_info_id)
        self.base_url = f"{self.conn_info.protocol}://{self.conn_info.ip}"
        self.headers = self.get_headers()

    def get_headers(self):
        # Basic Auth example
        import base64
        creds = f"{self.conn_info.username}:{self.conn_info.password}"
        auth = base64.b64encode(creds.encode()).decode()
        return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    def request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        r = requests.request(method, url, headers=self.headers, json=data, verify=False)
        r.raise_for_status()
        return r.json()

    def sync_to_resource(self, resource: Resource, data):
        # Map external data to CloudBolt custom fields
        for key, value in data.items():
            resource.set_value_for_custom_field(f"my_integration_{key}", value)

## Template: Cascading UI Option

```python
def generate_options_for_my_field(field, control_value=None, **kwargs):
    if not control_value:
        return [("", "------First, select a dependency------")]
    # Logic using MyIntegration(control_value)
    return [("id", "Name")]
```
```
