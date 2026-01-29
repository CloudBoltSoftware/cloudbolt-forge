---
description: How to create a new CloudBolt XUI extension
---

# Create a New XUI Extension

This workflow guides you through scaffolding a new XUI extension in the `xui/` directory.

## Steps

1. **Choose a Name**: Select a unique, lowercase name with underscores (e.g., `my_new_extension`).
2. **Create Directory Structure**:
   ```bash
   mkdir -p xui/<name>/templates/xui/<name>
   mkdir -p xui/<name>/static/
   touch xui/<name>/__init__.py
   touch xui/<name>/views.py
   touch xui/<name>/urls.py
   ```
3. **Define URLs**: Add a `urlpatterns` list to `urls.py`.
4. **Register in Global URLs**: Ensure the new extension is imported into `xui/urls.py` if necessary (though many CloudBolt setups auto-discover these).
5. **Create a View**: Implement a basic view in `views.py`.
6. **Add a README**: Create `xui/<name>/README.md` with an overview and installation instructions.

## Template: basic `views.py`
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    return render(request, 'xui/<name>/dashboard.html', {})
```
