# CloudBolt Django 5.2.x / Python 3.12.x Compatibility Check

## Overview

This tool scans CloudBolt customer customizations to identify code that is incompatible with Django 5.2.x and Python 3.12.x. Running this check before upgrading helps ensure a smooth transition.

**Important:** These scripts automatically use the CloudBolt appliance's Python and Django environment. No manual environment setup is required.

## Quick Start

### Using the Bash Script (Recommended)

```bash
# Navigate to the scripts directory
cd /var/tmp

# Run the compatibility check (generates text report in /var/tmp/)
sudo ./run_compatibility_check.sh

# Or generate different formats
sudo ./run_compatibility_check.sh --format json
sudo ./run_compatibility_check.sh --format html

# Custom output location
sudo ./run_compatibility_check.sh --output /tmp/my_report.txt
```

**Default Output Location:** `/var/tmp/cloudbolt_compatibility_report_<timestamp>.txt`

### Run the compatibility check (Python)

You can run the scanner directly with Python (no `.sh` script required):

```bash
# From the directory containing the scripts
python django52_python312_compatibility_check.py


# Other formats
python django52_python312_compatibility_check.py --output-format json
python django52_python312_compatibility_check.py --output-format html

# Custom output file
python django52_python312_compatibility_check.py --output-file /tmp/my_report.txt
```

## Auto-Fix Tool

After running the compatibility check, you can automatically fix many issues. **Manual fixes are still required** for issues the script cannot change safely; always review the scanner report and fix remaining items manually

### Using the Bash Script

```bash
# Preview changes without modifying files (RECOMMENDED FIRST)
sudo ./run_auto_fix.sh --dry-run

# Apply fixes (creates backups automatically)
sudo ./run_auto_fix.sh

# Apply fixes with verbose output
sudo ./run_auto_fix.sh --verbose
```

### Run the auto-fix (Python)

You can run the auto-fix script directly with Python:

```bash
# Preview changes without modifying files (run this first)
python django52_python312_auto_fix.py --dry-run

# Apply fixes (creates backups by default)
python django52_python312_auto_fix.py

# With verbose output
python django52_python312_auto_fix.py --verbose
```

**Backup Location:** `/var/tmp/cloudbolt_compatibility_backups/`

### Manual fixes still required

The auto-fix script only applies changes it can do safely. The following **require manual changes** (see also the docstring at the top of `django52_python312_auto_fix.py`):

| Item | What to do |
|------|------------|
| **rest_framework_jwt** | Migrate to `djangorestframework-simplejwt`. |
| **render_to_response(...) calls** | Add `request` as first argument to `render()`. |
| **imp module** | Use `importlib` instead. |
| **six.moves** | Replace with direct imports per case. |
| **Meta.index_together** | Use `Meta.indexes`. |
| **PickleSerializer** | Use `JSONSerializer` or a custom serializer. |
| **default_app_config, MIDDLEWARE_CLASSES** | Update app config and middleware structure. |
| **asyncio.coroutine, Task.all_tasks/current_task** | Use `async def`, `asyncio.all_tasks` / `asyncio.current_task`. |
| **length_is template filter** | Use `length` filter with comparison. |
| **pytz.UnknownTimeZoneError** | Use `KeyError` or `ZoneInfoNotFoundError`. |
| **datetime.now() / datetime.utcnow()** | Use CloudBolt `utilities.datetime` if required. |
| **assertFormError, crispy-forms, reversion, taggit** | Follow each package’s migration guide. |
| **Related filter on unsaved instance** | Save the instance first or use `.pk`; see Admin > Compatibility Warning Messages. |

## Backup and Restore

### Automatic Backups

The auto-fix tool **creates backups by default** before modifying any files. This ensures you can always restore your original code if needed.

| Mode | Backups Created? | Changes Made? |
|------|------------------|---------------|
| Default (`./run_auto_fix.sh`) |  Yes | Yes |
| Dry Run (`--dry-run`) | No | No (preview only) |
| No Backup (`--no-backup`) |  No |  Yes (not recommended) |

### Backup Location

All backups are saved to:
```
/var/tmp/cloudbolt_compatibility_backups/
```

Backup files are named with the original path and timestamp:
```
var_opt_cloudbolt_proserv_my_plugin.py.20260204_143022.bak
```

### How to Restore Files

If you need to restore a file to its original state:

```bash
# List all backups
ls -la /var/tmp/cloudbolt_compatibility_backups/

# Find backups for a specific file
ls /var/tmp/cloudbolt_compatibility_backups/ | grep "my_plugin"

# Restore a file
cp /var/tmp/cloudbolt_compatibility_backups/var_opt_cloudbolt_proserv_my_plugin.py.20260204_143022.bak \
   /var/opt/cloudbolt/proserv/my_plugin.py

# Restore all backups (use with caution)
cd /var/tmp/cloudbolt_compatibility_backups/
for f in *.bak; do
    original_path=$(echo "$f" | sed 's/\./\//g' | sed 's/_bak$//' | sed 's/^/\//')
    echo "Would restore: $f -> $original_path"
done
```

### Best Practice Workflow

1. **Run dry-run first** to preview changes:
   ```bash
   sudo ./run_auto_fix.sh --dry-run
   ```

2. **Review the preview** output carefully

3. **Apply fixes** (with automatic backups):
   ```bash
   sudo ./run_auto_fix.sh
   ```

4. **Test your CloudBolt instance** thoroughly

5. **If issues occur**, restore from backups

6. **Run the compatibility check again** to verify:
   ```bash
   sudo ./run_compatibility_check.sh
   ```

## Command Line Options

### Compatibility Check Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-format` | Report format: `json`, `html`, or `text` | `text` |
| `--output-file` | Custom output file path | `/var/tmp/cloudbolt_compatibility_report_<timestamp>.<ext>` |
| `--verbose` / `-v` | Show detailed scanning progress | Off |
| `--scan-database` | Scan plugins stored in database | On |
| `--additional-paths` | Extra directories to scan | None |

### Auto-Fix Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Show what would be changed without making changes | Off |
| `--no-backup` | Skip creating backup files (not recommended) | Off |
| `--verbose` / `-v` | Show detailed progress | Off |

## What Gets Scanned

### Automatically Scanned Directories

1. **Customer Settings & Customizations**
   - `/var/opt/cloudbolt/proserv/` - Custom settings, templates, XUI
   - `/var/opt/cloudbolt/proserv/templates/` - Custom templates
   - `/var/opt/cloudbolt/proserv/xui/` - UI Extensions

2. **Uploaded Code**
   - `/var/www/html/cloudbolt/static/uploads/hooks/` - Uploaded plugins
   - `/var/www/html/cloudbolt/static/uploads/shared_modules/` - Shared modules

3. **Database-Stored Code** (when Django is available)
   - CloudBolt Plug-ins
   - Server Actions
   - Resource Actions
   - Shared Modules

## Understanding the Report

### Severity Levels

| Level | Meaning | Action Required |
|-------|---------|-----------------|
|  **CRITICAL** | Code will fail immediately after upgrade | **MUST fix before upgrading** |
|  **HIGH** | Deprecated code that may cause issues | Should fix before upgrading |
|  **MEDIUM** | Deprecated but still functional | Fix when possible |
|  **LOW** | Minor issues or style recommendations | Optional |
|  **INFO** | Informational notes | No action required |

### Common Issues and Fixes

#### CRITICAL Issues

1. **`django.conf.urls.url()` removed**
   ```python
   # OLD (will break)
   from django.conf.urls import url
   url(r'^api/', include('api.urls'))
   
   # NEW (Django 5.2 compatible)
   from django.urls import path, re_path
   path('api/', include('api.urls'))
   # or for regex patterns:
   re_path(r'^api/', include('api.urls'))
   ```

2. **`MemcachedCache` backend removed**
   ```python
   # OLD (in customer_settings.py)
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
           ...
       }
   }
   
   # NEW
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
           ...
       }
   }
   ```

3. **`rest_framework_jwt` incompatible**
   ```python
   # OLD (unmaintained package)
   from rest_framework_jwt.authentication import JSONWebTokenAuthentication
   
   # NEW (use djangorestframework-simplejwt)
   from rest_framework_simplejwt.authentication import JWTAuthentication
   ```

4. **`distutils` removed in Python 3.12**
   ```python
   # OLD
   from distutils.version import LooseVersion
   
   # NEW
   from packaging.version import Version
   ```

#### HIGH Priority Issues

1. **Translation functions**
   ```python
   # OLD
   from django.utils.translation import ugettext as _
   from django.utils.translation import ugettext_lazy as _lazy
   
   # NEW
   from django.utils.translation import gettext as _
   from django.utils.translation import gettext_lazy as _lazy
   ```

2. **`six` library (Python 2/3 compatibility)**
   ```python
   # OLD
   import six
   message = six.text_type("Hello")
   
   # NEW
   message = str("Hello")
   ```

3. **`NullBooleanField` removed**
   ```python
   # OLD
   field = models.NullBooleanField()
   
   # NEW
   field = models.BooleanField(null=True)
   ```

4. **`request.is_ajax()` removed**
   ```python
   # OLD
   if request.is_ajax():
       ...
   
   # NEW
   if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
       ...
   ```

## Sample Report Output

### Text Report (Default)
```
================================================================================
CLOUDBOLT DJANGO 5.2.x / PYTHON 3.12.x COMPATIBILITY REPORT
================================================================================

Scan Date: 2024-01-15 10:30:00
Total Files Scanned: 50
Total Issues Found: 15

  CRITICAL: 3
  HIGH:     5
  MEDIUM:   4
  LOW:      3

--------------------------------------------------------------------------------
DETAILED FINDINGS
--------------------------------------------------------------------------------

FILE: /var/opt/cloudbolt/proserv/my_plugin.py
  Line 5: [HIGH] ugettext_import
    Description: ugettext is deprecated and removed in Django 4.0
    Found: from django.utils.translation import ugettext as _
    Fix: Use: from django.utils.translation import gettext as _
```

### JSON Report
```json
{
  "scan_date": "2024-01-15 10:30:00",
  "total_issues": 15,
  "critical_count": 3,
  "high_count": 5,
  "scan_results": [
    {
      "file_path": "/var/opt/cloudbolt/proserv/my_plugin.py",
      "issues": [
        {
          "line_number": 5,
          "issue_type": "ugettext_import",
          "severity": "HIGH",
          "description": "ugettext is deprecated...",
          "recommended_fix": "Use: from django.utils.translation import gettext as _"
        }
      ]
    }
  ]
}
```

### HTML Report
The HTML report provides a visual dashboard with:
- Summary statistics
- Issues grouped by severity
- Issues grouped by type
- Detailed findings with line numbers and suggested fixes

## Manual Code Search

If you prefer to manually search for issues, use these commands:

```bash
# Search for deprecated Django patterns
grep -r "from django.conf.urls import url" /var/opt/cloudbolt/proserv/
grep -r "ugettext" /var/opt/cloudbolt/proserv/
grep -r "MemcachedCache" /var/opt/cloudbolt/proserv/
grep -r "NullBooleanField" /var/opt/cloudbolt/proserv/

# Search for Python 3.12 issues
grep -r "import six" /var/opt/cloudbolt/proserv/
grep -r "import distutils" /var/opt/cloudbolt/proserv/
grep -r "import imp" /var/opt/cloudbolt/proserv/

# Search uploaded hooks
grep -r "ugettext" /var/www/html/cloudbolt/static/uploads/hooks/
```

## Troubleshooting

### Permission Denied
Run as root or cloudbolt user:
```bash
sudo ./run_compatibility_check.sh
```

### Django Not Available
The scanner can run without Django but won't scan database-stored plugins. On a CloudBolt appliance, Django should be available automatically.

### Script Not Found
Ensure you're running from the correct directory:
```bash
cd /var/tmp/upgrade_diagnostics/scripts/
ls -la *.sh *.py
```

### Python Not at Expected Path
If CloudBolt's Python is installed in a different location, you can specify it:
```bash
/path/to/your/python django52_python312_compatibility_check.py
```

## Files Provided

| File | Description |
|------|-------------|
| `django52_python312_compatibility_check.py` | Main compatibility scanner |
| `run_compatibility_check.sh` | Bash wrapper for easy execution |
| `django52_python312_auto_fix.py` | Automatic fix tool |
| `run_auto_fix.sh` | Bash wrapper for auto-fix |
| `README_compatibility_check.md` | This documentation |

## Support

For assistance with compatibility issues:
- CloudBolt Documentation: https://docs.cloudbolt.io
- CloudBolt Forge (examples): https://github.com/CloudBoltSoftware/cloudbolt-forge
- Contact CloudBolt Support

## Version History

- **1.0.2** - Added Django 5.x patterns, timezone/datetime patterns, package patterns, and expanded auto-fix rules
- **1.0.1** - Scripts now auto-configure CloudBolt environment (no manual setup needed)
- **1.0.0** - Initial release with Django 5.2.x and Python 3.12.x checks
