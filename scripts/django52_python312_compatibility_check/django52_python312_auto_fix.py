#!/usr/bin/env python3
"""
Django 5.2.x and Python 3.12.x Auto-Fix Script for CloudBolt

This script automatically fixes compatibility issues found by the compatibility scanner.
It creates backups before making any changes and generates a detailed fix report.

Usage:
    ./django52_python312_auto_fix.py [options]

Options:
    --dry-run           Show what would be changed without making changes
    --no-backup         Skip creating backup files (not recommended)
    --report-file       Path to JSON report from compatibility scanner
    --scan-and-fix      Scan and fix in one pass (default)
    --output-file       Path for the fix report

Run as root or cloudbolt user to access all directories.
This script can use CloudBolt's Django environment if available, or run standalone.

Author: Maryam Faiz
Version: 1.0.3
"""

import os
import sys

# =============================================================================
# AUTO-CONFIGURE CLOUDBOLT ENVIRONMENT
# =============================================================================
# This ensures the script works without manual environment setup

CB_ROOT = "/opt/cloudbolt"
CB_SRC = os.path.join(CB_ROOT, "src")
CB_VENV = os.path.join(CB_ROOT, "venv")

# Add CloudBolt source to Python path
if os.path.isdir(CB_SRC) and CB_SRC not in sys.path:
    sys.path.insert(0, CB_SRC)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# =============================================================================
# FIX DEFINITIONS
# =============================================================================

@dataclass
class FixResult:
    """Result of applying a fix to a file."""
    file_path: str
    original_line: str
    fixed_line: str
    line_number: int
    fix_type: str
    success: bool
    message: str = ""


@dataclass
class FileFixReport:
    """Report of all fixes applied to a single file."""
    file_path: str
    backup_path: Optional[str]
    fixes_applied: List[FixResult] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def fix_count(self) -> int:
        return len([f for f in self.fixes_applied if f.success])


class AutoFixer:
    """Automatically fixes Django and Python compatibility issues."""

    # Define fix patterns: (pattern_to_find, replacement, fix_type, description)
    FIX_PATTERNS = [
        # Django URL imports - handle various import styles
        {
            'pattern': r'^(\s*)from django\.conf\.urls import url\s*$',
            'replacement': r'\1from django.urls import re_path',
            'fix_type': 'url_import_simple',
            'description': 'Replace url import with re_path',
        },
        {
            'pattern': r'^(\s*)from django\.conf\.urls import url,\s*include\s*$',
            'replacement': r'\1from django.urls import re_path, include',
            'fix_type': 'url_import_with_include',
            'description': 'Replace url import with re_path (with include)',
        },
        {
            'pattern': r'^(\s*)from django\.conf\.urls import include,\s*url\s*$',
            'replacement': r'\1from django.urls import include, re_path',
            'fix_type': 'url_import_include_first',
            'description': 'Replace url import with re_path (include first)',
        },
        {
            'pattern': r'^(\s*)from django\.conf\.urls import (\w+(?:,\s*\w+)*),\s*url\s*$',
            'replacement': r'\1from django.urls import \2, re_path',
            'fix_type': 'url_import_multi',
            'description': 'Replace url import with re_path (multiple imports)',
        },
        {
            'pattern': r'^(\s*)from django\.conf\.urls import url,\s*(\w+(?:,\s*\w+)*)\s*$',
            'replacement': r'\1from django.urls import re_path, \2',
            'fix_type': 'url_import_multi_after',
            'description': 'Replace url import with re_path (url first)',
        },
        
        # Translation imports
        {
            'pattern': r'^(\s*)from django\.utils\.translation import ugettext as (_\w*)\s*$',
            'replacement': r'\1from django.utils.translation import gettext as \2',
            'fix_type': 'ugettext_import',
            'description': 'Replace ugettext with gettext',
        },
        {
            'pattern': r'^(\s*)from django\.utils\.translation import ugettext_lazy as (_\w*)\s*$',
            'replacement': r'\1from django.utils.translation import gettext_lazy as \2',
            'fix_type': 'ugettext_lazy_import',
            'description': 'Replace ugettext_lazy with gettext_lazy',
        },
        {
            'pattern': r'^(\s*)from django\.utils\.translation import ugettext\s*$',
            'replacement': r'\1from django.utils.translation import gettext',
            'fix_type': 'ugettext_import_plain',
            'description': 'Replace ugettext with gettext',
        },
        {
            'pattern': r'^(\s*)from django\.utils\.translation import ugettext_lazy\s*$',
            'replacement': r'\1from django.utils.translation import gettext_lazy',
            'fix_type': 'ugettext_lazy_import_plain',
            'description': 'Replace ugettext_lazy with gettext_lazy',
        },
        
        # Encoding imports
        {
            'pattern': r'^(\s*)from django\.utils\.encoding import (.*)force_text(.*)$',
            'replacement': r'\1from django.utils.encoding import \2force_str\3',
            'fix_type': 'force_text_import',
            'description': 'Replace force_text with force_str in import',
        },
        {
            'pattern': r'^(\s*)from django\.utils\.encoding import (.*)smart_text(.*)$',
            'replacement': r'\1from django.utils.encoding import \2smart_str\3',
            'fix_type': 'smart_text_import',
            'description': 'Replace smart_text with smart_str in import',
        },
        
        # Function calls - force_text/smart_text
        {
            'pattern': r'\bforce_text\s*\(',
            'replacement': 'force_str(',
            'fix_type': 'force_text_call',
            'description': 'Replace force_text() with force_str()',
        },
        {
            'pattern': r'\bsmart_text\s*\(',
            'replacement': 'smart_str(',
            'fix_type': 'smart_text_call',
            'description': 'Replace smart_text() with smart_str()',
        },
        
        # Six library - imports
        {
            'pattern': r'^(\s*)import six\s*$',
            'replacement': r'\1# import six  # Removed - use native Python 3',
            'fix_type': 'six_import',
            'description': 'Comment out six import',
        },
        {
            'pattern': r'^(\s*)from six import text_type\s*$',
            'replacement': r'\1# from six import text_type  # Removed - use str',
            'fix_type': 'six_text_type_import',
            'description': 'Comment out six.text_type import',
        },
        {
            'pattern': r'^(\s*)from six import string_types\s*$',
            'replacement': r'\1# from six import string_types  # Removed - use str',
            'fix_type': 'six_string_types_import',
            'description': 'Comment out six.string_types import',
        },
        
        # Six library - usage
        {
            'pattern': r'\bsix\.text_type\b',
            'replacement': 'str',
            'fix_type': 'six_text_type_usage',
            'description': 'Replace six.text_type with str',
        },
        {
            'pattern': r'\bsix\.string_types\b',
            'replacement': 'str',
            'fix_type': 'six_string_types_usage',
            'description': 'Replace six.string_types with str',
        },
        
        # MemcachedCache backend
        {
            'pattern': r'django\.core\.cache\.backends\.memcached\.MemcachedCache',
            'replacement': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'fix_type': 'memcached_backend',
            'description': 'Replace MemcachedCache with PyMemcacheCache',
        },
        
        # NullBooleanField
        {
            'pattern': r'\bmodels\.NullBooleanField\s*\(',
            'replacement': 'models.BooleanField(null=True, ',
            'fix_type': 'null_boolean_field',
            'description': 'Replace NullBooleanField with BooleanField(null=True)',
        },
        {
            'pattern': r'\bNullBooleanField\s*\(',
            'replacement': 'BooleanField(null=True, ',
            'fix_type': 'null_boolean_field_short',
            'description': 'Replace NullBooleanField with BooleanField(null=True)',
        },
        
        # request.is_ajax()
        {
            'pattern': r'request\.is_ajax\s*\(\s*\)',
            'replacement': "request.headers.get('X-Requested-With') == 'XMLHttpRequest'",
            'fix_type': 'is_ajax',
            'description': 'Replace request.is_ajax() with headers check',
        },
        
        # render_to_response (import only; render_to_response()→render() needs request added manually)
        {
            'pattern': r'^(\s*)from django\.shortcuts import (.*)render_to_response(.*)$',
            'replacement': r'\1from django.shortcuts import \2render\3',
            'fix_type': 'render_to_response_import',
            'description': 'Replace render_to_response import with render',
        },
        
        # distutils (Python 3.12)
        {
            'pattern': r'^(\s*)from distutils\.version import LooseVersion\s*$',
            'replacement': r'\1from packaging.version import Version  # Changed from distutils',
            'fix_type': 'distutils_looseversion',
            'description': 'Replace distutils.version with packaging.version',
        },
        {
            'pattern': r'^(\s*)from distutils\.version import StrictVersion\s*$',
            'replacement': r'\1from packaging.version import Version  # Changed from distutils',
            'fix_type': 'distutils_strictversion',
            'description': 'Replace distutils.version with packaging.version',
        },
        
        # collections ABCs (Python 3.10+)
        {
            'pattern': r'\bcollections\.Callable\b',
            'replacement': 'collections.abc.Callable',
            'fix_type': 'collections_callable',
            'description': 'Replace collections.Callable with collections.abc.Callable',
        },
        {
            'pattern': r'\bcollections\.Iterable\b',
            'replacement': 'collections.abc.Iterable',
            'fix_type': 'collections_iterable',
            'description': 'Replace collections.Iterable with collections.abc.Iterable',
        },
        {
            'pattern': r'\bcollections\.Mapping\b',
            'replacement': 'collections.abc.Mapping',
            'fix_type': 'collections_mapping',
            'description': 'Replace collections.Mapping with collections.abc.Mapping',
        },
        {
            'pattern': r'\bcollections\.MutableMapping\b',
            'replacement': 'collections.abc.MutableMapping',
            'fix_type': 'collections_mutablemapping',
            'description': 'Replace collections.MutableMapping with collections.abc.MutableMapping',
        },
        {
            'pattern': r'\bcollections\.Sequence\b',
            'replacement': 'collections.abc.Sequence',
            'fix_type': 'collections_sequence',
            'description': 'Replace collections.Sequence with collections.abc.Sequence',
        },
        {
            'pattern': r'\bcollections\.MutableSequence\b',
            'replacement': 'collections.abc.MutableSequence',
            'fix_type': 'collections_mutablesequence',
            'description': 'Replace collections.MutableSequence with collections.abc.MutableSequence',
        },
        {
            'pattern': r'\bcollections\.Set\b',
            'replacement': 'collections.abc.Set',
            'fix_type': 'collections_set',
            'description': 'Replace collections.Set with collections.abc.Set',
        },
        {
            'pattern': r'\bcollections\.MutableSet\b',
            'replacement': 'collections.abc.MutableSet',
            'fix_type': 'collections_mutableset',
            'description': 'Replace collections.MutableSet with collections.abc.MutableSet',
        },
        {
            'pattern': r'\bcollections\.Iterator\b',
            'replacement': 'collections.abc.Iterator',
            'fix_type': 'collections_iterator',
            'description': 'Replace collections.Iterator with collections.abc.Iterator',
        },
        {
            'pattern': r'\bcollections\.Generator\b',
            'replacement': 'collections.abc.Generator',
            'fix_type': 'collections_generator',
            'description': 'Replace collections.Generator with collections.abc.Generator',
        },
        {
            'pattern': r'\bcollections\.Hashable\b',
            'replacement': 'collections.abc.Hashable',
            'fix_type': 'collections_hashable',
            'description': 'Replace collections.Hashable with collections.abc.Hashable',
        },
        {
            'pattern': r'\bcollections\.Reversible\b',
            'replacement': 'collections.abc.Reversible',
            'fix_type': 'collections_reversible',
            'description': 'Replace collections.Reversible with collections.abc.Reversible',
        },
        {
            'pattern': r'\bcollections\.Container\b',
            'replacement': 'collections.abc.Container',
            'fix_type': 'collections_container',
            'description': 'Replace collections.Container with collections.abc.Container',
        },
        
        # =============================================================================
        # DJANGO 5.0+ SPECIFIC FIXES
        # =============================================================================
        
        # django.utils.timezone.utc deprecation
        {
            'pattern': r'from django\.utils\.timezone import utc\b',
            'replacement': 'from datetime import timezone; UTC = timezone.utc  # Changed from django.utils.timezone.utc',
            'fix_type': 'timezone_utc_import',
            'description': 'Replace django.utils.timezone.utc import with datetime.timezone.utc',
        },
        {
            'pattern': r'django\.utils\.timezone\.utc\b',
            'replacement': 'datetime.timezone.utc',
            'fix_type': 'timezone_utc_usage',
            'description': 'Replace django.utils.timezone.utc with datetime.timezone.utc',
        },
        
        # is_authenticated() / is_anonymous() - should be properties, not methods
        {
            'pattern': r'\.is_authenticated\s*\(\s*\)',
            'replacement': '.is_authenticated',
            'fix_type': 'is_authenticated_method',
            'description': 'Replace is_authenticated() method call with property access',
        },
        {
            'pattern': r'\.is_anonymous\s*\(\s*\)',
            'replacement': '.is_anonymous',
            'fix_type': 'is_anonymous_method',
            'description': 'Replace is_anonymous() method call with property access',
        },
        
        # =============================================================================
        # TIMEZONE PATTERNS (pytz → zoneinfo)
        # =============================================================================
        
        # pytz imports
        {
            'pattern': r'^(\s*)import pytz\s*$',
            'replacement': r'\1from zoneinfo import ZoneInfo  # Changed from pytz',
            'fix_type': 'pytz_import',
            'description': 'Replace import pytz with from zoneinfo import ZoneInfo',
        },
        {
            'pattern': r'^(\s*)from pytz import timezone\s*$',
            'replacement': r'\1from zoneinfo import ZoneInfo  # Changed from pytz.timezone',
            'fix_type': 'pytz_timezone_import',
            'description': 'Replace from pytz import timezone with ZoneInfo',
        },
        {
            'pattern': r'^(\s*)from pytz import utc\s*$',
            'replacement': r'\1from zoneinfo import ZoneInfo; UTC = ZoneInfo("UTC")  # Changed from pytz.utc',
            'fix_type': 'pytz_utc_import',
            'description': 'Replace from pytz import utc with ZoneInfo("UTC")',
        },
        
        # pytz.timezone() calls
        {
            'pattern': r'pytz\.timezone\s*\(\s*(["\'][^"\']+["\'])\s*\)',
            'replacement': r'ZoneInfo(\1)',
            'fix_type': 'pytz_timezone_call',
            'description': 'Replace pytz.timezone() with ZoneInfo()',
        },
        
        # pytz.utc usage
        {
            'pattern': r'\bpytz\.utc\b',
            'replacement': 'ZoneInfo("UTC")',
            'fix_type': 'pytz_utc_usage',
            'description': 'Replace pytz.utc with ZoneInfo("UTC")',
        },
        
        # pytz.UTC usage
        {
            'pattern': r'\bpytz\.UTC\b',
            'replacement': 'ZoneInfo("UTC")',
            'fix_type': 'pytz_UTC_usage',
            'description': 'Replace pytz.UTC with ZoneInfo("UTC")',
        },
        
        # =============================================================================
        # JSONField import change
        # =============================================================================
        {
            'pattern': r'^(\s*)from django\.contrib\.postgres\.fields import JSONField\s*$',
            'replacement': r'\1from django.db.models import JSONField  # Changed from postgres.fields',
            'fix_type': 'postgres_jsonfield_import',
            'description': 'Replace postgres.fields.JSONField import with db.models.JSONField',
        },
        {
            'pattern': r'django\.contrib\.postgres\.fields\.JSONField',
            'replacement': 'django.db.models.JSONField',
            'fix_type': 'postgres_jsonfield_usage',
            'description': 'Replace postgres.fields.JSONField with db.models.JSONField',
        },
        
        # =============================================================================
        # USE_L10N setting removal
        # =============================================================================
        {
            'pattern': r'^(\s*)USE_L10N\s*=\s*True\s*$',
            'replacement': r'\1# USE_L10N = True  # Removed - always True in Django 4.0+',
            'fix_type': 'use_l10n_true',
            'description': 'Comment out USE_L10N = True (always True in Django 4.0+)',
        },
        {
            'pattern': r'^(\s*)USE_L10N\s*=\s*False\s*$',
            'replacement': r'\1# USE_L10N = False  # Removed - always True in Django 4.0+',
            'fix_type': 'use_l10n_false',
            'description': 'Comment out USE_L10N = False (always True in Django 4.0+)',
        },
        
        # =============================================================================
        # typing module deprecations (Python 3.9+)
        # =============================================================================
        {
            'pattern': r'\btyping\.Dict\b',
            'replacement': 'dict',
            'fix_type': 'typing_dict',
            'description': 'Replace typing.Dict with built-in dict',
        },
        {
            'pattern': r'\btyping\.List\b',
            'replacement': 'list',
            'fix_type': 'typing_list',
            'description': 'Replace typing.List with built-in list',
        },
        {
            'pattern': r'\btyping\.Tuple\b',
            'replacement': 'tuple',
            'fix_type': 'typing_tuple',
            'description': 'Replace typing.Tuple with built-in tuple',
        },
        {
            'pattern': r'\btyping\.Set\b',
            'replacement': 'set',
            'fix_type': 'typing_set',
            'description': 'Replace typing.Set with built-in set',
        },
        {
            'pattern': r'\btyping\.FrozenSet\b',
            'replacement': 'frozenset',
            'fix_type': 'typing_frozenset',
            'description': 'Replace typing.FrozenSet with built-in frozenset',
        },
        {
            'pattern': r'\btyping\.Type\b',
            'replacement': 'type',
            'fix_type': 'typing_type',
            'description': 'Replace typing.Type with built-in type',
        },
        
        # url() -> re_path() for regex patterns (complex cases may need manual review)
        {
            'pattern': r'\burl\s*\(\s*r(["\'])',
            'replacement': r're_path(r\1',
            'fix_type': 'url_function_call',
            'description': 'Replace url() with re_path() for regex patterns',
        },
        # Django 5.2: find(all=) -> find(find_all=)
        {
            'pattern': r'\.find\s*\(([^,]+),\s*all\s*=\s*',
            'replacement': r'.find(\1, find_all=',
            'fix_type': 'staticfiles_find_all',
            'description': "Replace deprecated 'all' with 'find_all' in find()",
        },
        # ArrayAgg/JSONBAgg/StringAgg: ordering= -> order_by=
        {
            'pattern': r'ArrayAgg\s*\(([^)]*)\bordering\s*=\s*',
            'replacement': r'ArrayAgg(\1order_by=',
            'fix_type': 'postgres_arrayagg_order_by',
            'description': "Replace 'ordering' with 'order_by' in ArrayAgg()",
        },
        {
            'pattern': r'JSONBAgg\s*\(([^)]*)\bordering\s*=\s*',
            'replacement': r'JSONBAgg(\1order_by=',
            'fix_type': 'postgres_jsonbagg_order_by',
            'description': "Replace 'ordering' with 'order_by' in JSONBAgg()",
        },
        {
            'pattern': r'StringAgg\s*\(([^)]*)\bordering\s*=\s*',
            'replacement': r'StringAgg(\1order_by=',
            'fix_type': 'postgres_stringagg_order_by',
            'description': "Replace 'ordering' with 'order_by' in StringAgg()",
        },
    ]
    
    def __init__(self, dry_run: bool = False, create_backup: bool = True, verbose: bool = False):
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.verbose = verbose
        self.backup_dir = '/var/tmp/cloudbolt_compatibility_backups'
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns."""
        for fix_info in self.FIX_PATTERNS:
            fix_info['compiled'] = re.compile(fix_info['pattern'], re.MULTILINE)
    
    def log(self, message: str):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[INFO] {message}")
    
    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create a backup of the file before modifying it."""
        if not self.create_backup:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Create backup filename preserving directory structure
        rel_path = file_path.replace('/', '_').lstrip('_')
        backup_path = os.path.join(self.backup_dir, f"{rel_path}.{timestamp}.bak")
        
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.log(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def fix_file(self, file_path: str) -> FileFixReport:
        """Apply all applicable fixes to a single file."""
        report = FileFixReport(file_path=file_path, backup_path=None)
        
        # Check if file exists
        if not os.path.exists(file_path):
            report.error = f"File not found: {file_path}"
            return report
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
                original_lines = original_content.split('\n')
        except Exception as e:
            report.error = f"Error reading file: {e}"
            return report
        
        # Track changes
        modified_content = original_content
        fixes_applied = []
        
        # Apply each fix pattern
        for fix_info in self.FIX_PATTERNS:
            compiled = fix_info['compiled']
            replacement = fix_info['replacement']
            fix_type = fix_info['fix_type']
            description = fix_info['description']
            
            # Find all matches
            matches = list(compiled.finditer(modified_content))
            
            for match in matches:
                original_text = match.group(0)
                
                # Apply replacement
                fixed_text = compiled.sub(replacement, original_text, count=1)
                
                if fixed_text != original_text:
                    # Find line number
                    line_start = modified_content[:match.start()].count('\n') + 1
                    
                    fix_result = FixResult(
                        file_path=file_path,
                        original_line=original_text.strip(),
                        fixed_line=fixed_text.strip(),
                        line_number=line_start,
                        fix_type=fix_type,
                        success=True,
                        message=description
                    )
                    fixes_applied.append(fix_result)
            
            # Apply all replacements for this pattern
            modified_content = compiled.sub(replacement, modified_content)
        
        # Check if any changes were made
        if modified_content != original_content:
            report.fixes_applied = fixes_applied
            
            if not self.dry_run:
                # Create backup
                report.backup_path = self._create_backup(file_path)
                
                # Write modified content
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    self.log(f"Fixed {len(fixes_applied)} issues in {file_path}")
                except Exception as e:
                    report.error = f"Error writing file: {e}"
                    # Mark all fixes as failed
                    for fix in report.fixes_applied:
                        fix.success = False
                        fix.message = f"Write failed: {e}"
            else:
                self.log(f"[DRY-RUN] Would fix {len(fixes_applied)} issues in {file_path}")
        
        return report
    
    def fix_directory(self, directory: str, extensions: Set[str] = None) -> List[FileFixReport]:
        """Apply fixes to all Python files in a directory."""
        if extensions is None:
            extensions = {'.py'}
        
        reports = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            self.log(f"Directory does not exist: {directory}")
            return reports
        
        for file_path in directory_path.rglob('*'):
            if file_path.suffix in extensions and file_path.is_file():
                # Skip __pycache__ and migration files
                if '__pycache__' in str(file_path):
                    continue
                if '/migrations/' in str(file_path) and file_path.name != '__init__.py':
                    continue
                
                self.log(f"Processing: {file_path}")
                report = self.fix_file(str(file_path))
                if report.fixes_applied or report.error:
                    reports.append(report)
        
        return reports
    
    def fix_from_report(self, report_path: str) -> List[FileFixReport]:
        """Fix issues from a JSON compatibility report."""
        reports = []
        
        try:
            with open(report_path, 'r') as f:
                scan_report = json.load(f)
        except Exception as e:
            print(f"Error loading report: {e}")
            return reports
        
        # Get unique files from the report
        files_to_fix = set()
        for scan_result in scan_report.get('scan_results', []):
            file_path = scan_result.get('file_path', '')
            # Handle database plugin paths
            if file_path.startswith('[Plugin:') or file_path.startswith('[SharedModule:'):
                # Extract actual path
                parts = file_path.split('] ')
                if len(parts) > 1:
                    file_path = parts[1]
            if file_path and os.path.exists(file_path):
                files_to_fix.add(file_path)
        
        for file_path in files_to_fix:
            self.log(f"Processing: {file_path}")
            report = self.fix_file(file_path)
            if report.fixes_applied or report.error:
                reports.append(report)
        
        return reports


def generate_fix_report(reports: List[FileFixReport], dry_run: bool = False) -> str:
    """Generate a text report of all fixes applied."""
    lines = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.append("=" * 80)
    lines.append("CLOUDBOLT COMPATIBILITY AUTO-FIX REPORT")
    if dry_run:
        lines.append("*** DRY-RUN MODE - NO CHANGES WERE MADE ***")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Report Generated: {timestamp}")
    lines.append("")
    
    # Summary
    total_files = len(reports)
    total_fixes = sum(r.fix_count for r in reports)
    files_with_errors = sum(1 for r in reports if r.error)
    
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Files Processed: {total_files}")
    lines.append(f"Total Fixes Applied: {total_fixes}")
    lines.append(f"Files with Errors: {files_with_errors}")
    lines.append("")
    
    # Fix type breakdown
    fix_types = defaultdict(int)
    for report in reports:
        for fix in report.fixes_applied:
            if fix.success:
                fix_types[fix.fix_type] += 1
    
    if fix_types:
        lines.append("-" * 80)
        lines.append("FIXES BY TYPE")
        lines.append("-" * 80)
        for fix_type, count in sorted(fix_types.items(), key=lambda x: -x[1]):
            lines.append(f"  {fix_type}: {count}")
        lines.append("")
    
    # Detailed report
    lines.append("-" * 80)
    lines.append("DETAILED CHANGES")
    lines.append("-" * 80)
    
    for report in reports:
        if report.fixes_applied or report.error:
            lines.append("")
            lines.append(f"FILE: {report.file_path}")
            
            if report.backup_path:
                lines.append(f"  Backup: {report.backup_path}")
            
            if report.error:
                lines.append(f"  ERROR: {report.error}")
            
            for fix in report.fixes_applied:
                status = "✓" if fix.success else "✗"
                lines.append(f"  {status} Line {fix.line_number}: {fix.fix_type}")
                lines.append(f"      Before: {fix.original_line[:70]}...")
                lines.append(f"      After:  {fix.fixed_line[:70]}...")
    
    lines.append("")
    lines.append("=" * 80)
    
    if dry_run:
        lines.append("DRY-RUN COMPLETE - Re-run without --dry-run to apply changes")
    else:
        lines.append("FIX COMPLETE - Review changes and test your code")
        lines.append(f"Backups saved to: /var/tmp/cloudbolt_compatibility_backups/")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Automatically fix Django 5.2.x and Python 3.12.x compatibility issues'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup files (not recommended)'
    )
    parser.add_argument(
        '--report-file',
        help='Path to JSON report from compatibility scanner'
    )
    parser.add_argument(
        '--output-file',
        help='Path for the fix report'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--additional-paths',
        nargs='*',
        help='Additional paths to scan and fix'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("CloudBolt Django 5.2.x / Python 3.12.x Auto-Fix Tool")
    print("=" * 60)
    
    if args.dry_run:
        print("*** DRY-RUN MODE - No changes will be made ***")
    
    print("")
    
    # Initialize fixer
    fixer = AutoFixer(
        dry_run=args.dry_run,
        create_backup=not args.no_backup,
        verbose=args.verbose
    )
    
    all_reports = []
    
    # If report file provided, fix from report
    if args.report_file:
        print(f"Fixing issues from report: {args.report_file}")
        reports = fixer.fix_from_report(args.report_file)
        all_reports.extend(reports)
    else:
        # Standard customer directories to scan
        customer_directories = [
            '/var/opt/cloudbolt/proserv/',
            '/var/www/html/cloudbolt/static/uploads/hooks/',
            '/var/www/html/cloudbolt/static/uploads/shared_modules/',
        ]
        
        # Add additional paths if specified
        if args.additional_paths:
            customer_directories.extend(args.additional_paths)
        
        # Scan and fix directories
        for directory in customer_directories:
            if os.path.exists(directory):
                print(f"Processing directory: {directory}")
                reports = fixer.fix_directory(directory)
                all_reports.extend(reports)
                fix_count = sum(r.fix_count for r in reports)
                print(f"  Fixed {fix_count} issues in {len(reports)} files")
            else:
                print(f"Directory not found: {directory}")
    
    print("")
    
    # Generate report
    report_text = generate_fix_report(all_reports, dry_run=args.dry_run)
    
    # Output report
    output_dir = '/var/tmp'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_output = f'{output_dir}/cloudbolt_autofix_report_{timestamp}.txt'
    output_file = args.output_file or default_output
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(report_text)
    print("")
    print(f"Report saved to: {output_file}")
    
    # Summary
    total_fixes = sum(r.fix_count for r in all_reports)
    if total_fixes > 0:
        if args.dry_run:
            print(f"\n {total_fixes} fixes would be applied. Run without --dry-run to apply.")
        else:
            print(f"\n {total_fixes} fixes applied successfully.")
            print(f"   Backups saved to: {fixer.backup_dir}/")
    else:
        print("\n No compatibility issues found that could be auto-fixed.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

