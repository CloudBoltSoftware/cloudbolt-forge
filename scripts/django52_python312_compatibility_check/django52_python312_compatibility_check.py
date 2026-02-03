#!/usr/bin/env python3
"""
Django 5.2.x and Python 3.12.x Compatibility Check Script for CloudBolt

This script scans customer customizations to identify code that is incompatible
with Django 5.2.x and Python 3.12.x.

Usage:
    ./django52_python312_compatibility_check.py [--output-format json|html|text] [--output-file report.txt]

Run as root or cloudbolt user to access all directories.
This script can use CloudBolt's Django environment if available, or run standalone.

Author: Maryam Faiz
Version: 1.0.2
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
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# Try to import Django (should work on CloudBolt appliance)
DJANGO_AVAILABLE = False
try:
    import django
    django.setup()
    DJANGO_AVAILABLE = True
except Exception as e:
    # Django not available - scanner will still work but won't scan DB plugins
    pass


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class CompatibilityIssue:
    """Represents a single compatibility issue found in customer code."""
    file_path: str
    line_number: int
    issue_type: str
    severity: str
    description: str
    deprecated_code: str
    recommended_fix: str
    django_version: str = ""  # Version where deprecated/removed
    python_version: str = ""  # Python version affected
    
    def to_dict(self):
        return asdict(self)


@dataclass 
class ScanResult:
    """Results from scanning a single file."""
    file_path: str
    issues: List[CompatibilityIssue] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self):
        return {
            'file_path': self.file_path,
            'issues': [i.to_dict() for i in self.issues],
            'error': self.error
        }


@dataclass
class CompatibilityReport:
    """Complete compatibility report."""
    scan_date: str
    cloudbolt_version: str
    current_django_version: str
    current_python_version: str
    target_django_version: str
    target_python_version: str
    total_files_scanned: int
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    issues_by_type: Dict[str, int]
    scan_results: List[ScanResult]
    
    def to_dict(self):
        return {
            'scan_date': self.scan_date,
            'cloudbolt_version': self.cloudbolt_version,
            'current_django_version': self.current_django_version,
            'current_python_version': self.current_python_version,
            'target_django_version': self.target_django_version,
            'target_python_version': self.target_python_version,
            'total_files_scanned': self.total_files_scanned,
            'total_issues': self.total_issues,
            'critical_count': self.critical_count,
            'high_count': self.high_count,
            'medium_count': self.medium_count,
            'low_count': self.low_count,
            'info_count': self.info_count,
            'issues_by_type': self.issues_by_type,
            'scan_results': [r.to_dict() for r in self.scan_results if r.issues or r.error]
        }


# =============================================================================
# COMPATIBILITY PATTERNS
# =============================================================================

# Django 5.2.x Incompatible Patterns
DJANGO_PATTERNS = [
    # CRITICAL - Will fail immediately
    {
        'pattern': r'from\s+django\.conf\.urls\s+import\s+.*\burl\b',
        'issue_type': 'django.conf.urls.url_import',
        'severity': Severity.CRITICAL,
        'description': 'django.conf.urls.url() was removed in Django 4.0',
        'recommended_fix': 'Use: from django.urls import path, re_path',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'\burl\s*\(\s*r[\'"]',
        'issue_type': 'url_function_usage',
        'severity': Severity.CRITICAL,
        'description': 'url() function is removed. Use path() or re_path()',
        'recommended_fix': 'Replace url(r"^pattern/$", view) with path("pattern/", view) or re_path(r"^pattern/$", view)',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'django\.core\.cache\.backends\.memcached\.MemcachedCache',
        'issue_type': 'memcached_cache_backend',
        'severity': Severity.CRITICAL,
        'description': 'MemcachedCache backend was removed in Django 4.0',
        'recommended_fix': 'Use django.core.cache.backends.memcached.PyMemcacheCache',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'from\s+rest_framework_jwt',
        'issue_type': 'rest_framework_jwt_import',
        'severity': Severity.CRITICAL,
        'description': 'rest_framework_jwt is unmaintained and incompatible with Django 5.x',
        'recommended_fix': 'Migrate to djangorestframework-simplejwt',
        'django_version': '5.0+',
    },
    {
        'pattern': r'rest_framework_jwt\.',
        'issue_type': 'rest_framework_jwt_usage',
        'severity': Severity.CRITICAL,
        'description': 'rest_framework_jwt is unmaintained and incompatible with Django 5.x',
        'recommended_fix': 'Migrate to djangorestframework-simplejwt',
        'django_version': '5.0+',
    },
    
    # HIGH - Deprecated, will cause issues
    {
        'pattern': r'models\.NullBooleanField',
        'issue_type': 'null_boolean_field',
        'severity': Severity.HIGH,
        'description': 'NullBooleanField is removed in Django 4.0',
        'recommended_fix': 'Use BooleanField(null=True) instead',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'from\s+django\.utils\.translation\s+import\s+.*\bugettext\b',
        'issue_type': 'ugettext_import',
        'severity': Severity.HIGH,
        'description': 'ugettext is deprecated and removed in Django 4.0',
        'recommended_fix': 'Use: from django.utils.translation import gettext as _',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'from\s+django\.utils\.translation\s+import\s+.*\bugettext_lazy\b',
        'issue_type': 'ugettext_lazy_import',
        'severity': Severity.HIGH,
        'description': 'ugettext_lazy is deprecated and removed in Django 4.0',
        'recommended_fix': 'Use: from django.utils.translation import gettext_lazy as _',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'\bugettext\s*\(',
        'issue_type': 'ugettext_function',
        'severity': Severity.HIGH,
        'description': 'ugettext() function is removed in Django 4.0',
        'recommended_fix': 'Use gettext() instead',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'\bugettext_lazy\s*\(',
        'issue_type': 'ugettext_lazy_function',
        'severity': Severity.HIGH,
        'description': 'ugettext_lazy() function is removed in Django 4.0',
        'recommended_fix': 'Use gettext_lazy() instead',
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'\.is_ajax\s*\(\s*\)',
        'issue_type': 'is_ajax_method',
        'severity': Severity.HIGH,
        'description': 'HttpRequest.is_ajax() was removed in Django 4.0',
        'recommended_fix': "Use: request.headers.get('X-Requested-With') == 'XMLHttpRequest'",
        'django_version': '4.0 (removed)',
    },
    {
        'pattern': r'from\s+django\.utils\.encoding\s+import\s+.*\bforce_text\b',
        'issue_type': 'force_text_import',
        'severity': Severity.HIGH,
        'description': 'force_text is deprecated, use force_str',
        'recommended_fix': 'Use: from django.utils.encoding import force_str',
        'django_version': '4.0 (deprecated)',
    },
    {
        'pattern': r'from\s+django\.utils\.encoding\s+import\s+.*\bsmart_text\b',
        'issue_type': 'smart_text_import',
        'severity': Severity.HIGH,
        'description': 'smart_text is deprecated, use smart_str',
        'recommended_fix': 'Use: from django.utils.encoding import smart_str',
        'django_version': '4.0 (deprecated)',
    },
    {
        'pattern': r'\bforce_text\s*\(',
        'issue_type': 'force_text_function',
        'severity': Severity.HIGH,
        'description': 'force_text() is deprecated',
        'recommended_fix': 'Use force_str() instead',
        'django_version': '4.0 (deprecated)',
    },
    {
        'pattern': r'\bsmart_text\s*\(',
        'issue_type': 'smart_text_function',
        'severity': Severity.HIGH,
        'description': 'smart_text() is deprecated',
        'recommended_fix': 'Use smart_str() instead',
        'django_version': '4.0 (deprecated)',
    },
    
    # MEDIUM - Should be updated
    {
        'pattern': r'from\s+django\.contrib\.postgres\.fields\s+import\s+JSONField',
        'issue_type': 'postgres_jsonfield',
        'severity': Severity.MEDIUM,
        'description': 'JSONField should be imported from django.db.models',
        'recommended_fix': 'Use: from django.db.models import JSONField',
        'django_version': '3.1+',
    },
    {
        'pattern': r'default_app_config\s*=',
        'issue_type': 'default_app_config',
        'severity': Severity.MEDIUM,
        'description': 'default_app_config is deprecated in Django 3.2 and removed in 4.1',
        'recommended_fix': 'Remove default_app_config and use AppConfig class directly',
        'django_version': '4.1 (removed)',
    },
    {
        'pattern': r'USE_L10N\s*=',
        'issue_type': 'use_l10n_setting',
        'severity': Severity.MEDIUM,
        'description': 'USE_L10N setting is deprecated (always True in Django 4.0+)',
        'recommended_fix': 'Remove USE_L10N from settings',
        'django_version': '4.0 (deprecated)',
    },
    {
        'pattern': r'MIDDLEWARE_CLASSES\s*=',
        'issue_type': 'middleware_classes',
        'severity': Severity.CRITICAL,
        'description': 'MIDDLEWARE_CLASSES is removed, use MIDDLEWARE',
        'recommended_fix': 'Rename to MIDDLEWARE and update middleware format',
        'django_version': '2.0 (removed)',
    },
    {
        'pattern': r'from\s+django\.shortcuts\s+import\s+.*\brender_to_response\b',
        'issue_type': 'render_to_response',
        'severity': Severity.HIGH,
        'description': 'render_to_response is removed in Django 3.0',
        'recommended_fix': 'Use render() instead',
        'django_version': '3.0 (removed)',
    },
    {
        'pattern': r'\brender_to_response\s*\(',
        'issue_type': 'render_to_response_function',
        'severity': Severity.HIGH,
        'description': 'render_to_response() is removed in Django 3.0',
        'recommended_fix': 'Use render() instead',
        'django_version': '3.0 (removed)',
    },
    
]

# Python 3.12.x Incompatible Patterns
PYTHON_PATTERNS = [
    # CRITICAL - Will fail
    {
        'pattern': r'import\s+distutils',
        'issue_type': 'distutils_import',
        'severity': Severity.CRITICAL,
        'description': 'distutils module is removed in Python 3.12',
        'recommended_fix': 'Use setuptools or packaging module instead',
        'python_version': '3.12 (removed)',
    },
    {
        'pattern': r'from\s+distutils',
        'issue_type': 'distutils_from_import',
        'severity': Severity.CRITICAL,
        'description': 'distutils module is removed in Python 3.12',
        'recommended_fix': 'Use setuptools or packaging module instead',
        'python_version': '3.12 (removed)',
    },
    {
        'pattern': r'import\s+imp\b',
        'issue_type': 'imp_import',
        'severity': Severity.CRITICAL,
        'description': 'imp module is removed in Python 3.12',
        'recommended_fix': 'Use importlib instead',
        'python_version': '3.12 (removed)',
    },
    {
        'pattern': r'from\s+imp\s+import',
        'issue_type': 'imp_from_import',
        'severity': Severity.CRITICAL,
        'description': 'imp module is removed in Python 3.12',
        'recommended_fix': 'Use importlib instead',
        'python_version': '3.12 (removed)',
    },
    
    # HIGH - Deprecated
    {
        'pattern': r'import\s+six\b',
        'issue_type': 'six_import',
        'severity': Severity.HIGH,
        'description': 'six library is for Python 2/3 compatibility, unnecessary in Python 3.12',
        'recommended_fix': 'Remove six and use native Python 3 constructs',
        'python_version': '3.x',
    },
    {
        'pattern': r'from\s+six\s+import',
        'issue_type': 'six_from_import',
        'severity': Severity.HIGH,
        'description': 'six library is for Python 2/3 compatibility, unnecessary in Python 3.12',
        'recommended_fix': 'Remove six and use native Python 3 constructs',
        'python_version': '3.x',
    },
    {
        'pattern': r'six\.text_type',
        'issue_type': 'six_text_type',
        'severity': Severity.HIGH,
        'description': 'six.text_type is unnecessary in Python 3',
        'recommended_fix': 'Use str instead',
        'python_version': '3.x',
    },
    {
        'pattern': r'six\.string_types',
        'issue_type': 'six_string_types',
        'severity': Severity.HIGH,
        'description': 'six.string_types is unnecessary in Python 3',
        'recommended_fix': 'Use str instead',
        'python_version': '3.x',
    },
    {
        'pattern': r'six\.moves',
        'issue_type': 'six_moves',
        'severity': Severity.HIGH,
        'description': 'six.moves is unnecessary in Python 3',
        'recommended_fix': 'Import directly from the Python 3 module',
        'python_version': '3.x',
    },
    {
        'pattern': r'asyncio\.coroutine',
        'issue_type': 'asyncio_coroutine_decorator',
        'severity': Severity.HIGH,
        'description': '@asyncio.coroutine is removed in Python 3.11',
        'recommended_fix': 'Use async def instead',
        'python_version': '3.11 (removed)',
    },
    {
        'pattern': r'@asyncio\.coroutine',
        'issue_type': 'asyncio_coroutine_decorator',
        'severity': Severity.HIGH,
        'description': '@asyncio.coroutine decorator is removed in Python 3.11',
        'recommended_fix': 'Use async def instead',
        'python_version': '3.11 (removed)',
    },
    {
        'pattern': r'asyncio\.Task\.all_tasks',
        'issue_type': 'asyncio_all_tasks',
        'severity': Severity.MEDIUM,
        'description': 'asyncio.Task.all_tasks() is deprecated',
        'recommended_fix': 'Use asyncio.all_tasks() instead',
        'python_version': '3.9+',
    },
    {
        'pattern': r'asyncio\.Task\.current_task',
        'issue_type': 'asyncio_current_task',
        'severity': Severity.MEDIUM,
        'description': 'asyncio.Task.current_task() is deprecated',
        'recommended_fix': 'Use asyncio.current_task() instead',
        'python_version': '3.9+',
    },
    {
        'pattern': r'collections\.Callable',
        'issue_type': 'collections_abc',
        'severity': Severity.CRITICAL,
        'description': 'collections.Callable is removed in Python 3.10',
        'recommended_fix': 'Use collections.abc.Callable instead',
        'python_version': '3.10 (removed)',
    },
    {
        'pattern': r'collections\.(Awaitable|Coroutine|AsyncIterable|AsyncIterator|AsyncGenerator|Hashable|Iterable|Iterator|Generator|Reversible|Container|Collection|MutableSet|Set|MutableMapping|Mapping|MappingView|KeysView|ItemsView|ValuesView|MutableSequence|Sequence|ByteString)',
        'issue_type': 'collections_abc_classes',
        'severity': Severity.CRITICAL,
        'description': 'Abstract base classes moved from collections to collections.abc in Python 3.3, aliases removed in 3.10',
        'recommended_fix': 'Import from collections.abc instead',
        'python_version': '3.10 (removed)',
    },
    {
        'pattern': r'from\s+typing\s+import\s+.*\bDict\b',
        'issue_type': 'typing_dict',
        'severity': Severity.LOW,
        'description': 'typing.Dict is deprecated in Python 3.9+, use dict directly',
        'recommended_fix': 'Use dict[K, V] instead of Dict[K, V]',
        'python_version': '3.9+ (deprecated)',
    },
    {
        'pattern': r'from\s+typing\s+import\s+.*\bList\b',
        'issue_type': 'typing_list',
        'severity': Severity.LOW,
        'description': 'typing.List is deprecated in Python 3.9+, use list directly',
        'recommended_fix': 'Use list[T] instead of List[T]',
        'python_version': '3.9+ (deprecated)',
    },
    {
        'pattern': r'from\s+typing\s+import\s+.*\bTuple\b',
        'issue_type': 'typing_tuple',
        'severity': Severity.LOW,
        'description': 'typing.Tuple is deprecated in Python 3.9+, use tuple directly',
        'recommended_fix': 'Use tuple[T, ...] instead of Tuple[T, ...]',
        'python_version': '3.9+ (deprecated)',
    },
    {
        'pattern': r'from\s+typing\s+import\s+.*\bSet\b(?!\w)',
        'issue_type': 'typing_set',
        'severity': Severity.LOW,
        'description': 'typing.Set is deprecated in Python 3.9+, use set directly',
        'recommended_fix': 'Use set[T] instead of Set[T]',
        'python_version': '3.9+ (deprecated)',
    },
]

# Third-party library patterns that may cause issues
THIRD_PARTY_PATTERNS = [
    {
        'pattern': r'from\s+simplejson',
        'issue_type': 'simplejson_import',
        'severity': Severity.MEDIUM,
        'description': 'simplejson is rarely needed, standard json module is sufficient',
        'recommended_fix': 'Consider using standard library json module',
        'python_version': '3.x',
    },
    {
        'pattern': r'import\s+simplejson',
        'issue_type': 'simplejson_import',
        'severity': Severity.MEDIUM,
        'description': 'simplejson is rarely needed, standard json module is sufficient',
        'recommended_fix': 'Consider using standard library json module',
        'python_version': '3.x',
    },
]


class CompatibilityScanner:
    """Scans files for Django and Python compatibility issues."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.all_patterns = DJANGO_PATTERNS + PYTHON_PATTERNS + THIRD_PARTY_PATTERNS
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns for efficiency."""
        for pattern_info in self.all_patterns:
            pattern_info['compiled'] = re.compile(pattern_info['pattern'])
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[INFO] {message}")
    
    def scan_file(self, file_path: str) -> ScanResult:
        """Scan a single file for compatibility issues."""
        result = ScanResult(file_path=file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            result.error = f"Error reading file: {str(e)}"
            return result
        
        for pattern_info in self.all_patterns:
            compiled = pattern_info['compiled']
            for line_num, line in enumerate(lines, 1):
                matches = compiled.finditer(line)
                for match in matches:
                    issue = CompatibilityIssue(
                        file_path=file_path,
                        line_number=line_num,
                        issue_type=pattern_info['issue_type'],
                        severity=pattern_info['severity'].value,
                        description=pattern_info['description'],
                        deprecated_code=match.group(0).strip(),
                        recommended_fix=pattern_info['recommended_fix'],
                        django_version=pattern_info.get('django_version', ''),
                        python_version=pattern_info.get('python_version', ''),
                    )
                    result.issues.append(issue)
        
        return result
    
    def scan_directory(self, directory: str, extensions: Set[str] = None) -> List[ScanResult]:
        """Scan all Python files in a directory recursively."""
        if extensions is None:
            extensions = {'.py'}
        
        results = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            self.log(f"Directory does not exist: {directory}")
            return results
        
        for file_path in directory_path.rglob('*'):
            if file_path.suffix in extensions and file_path.is_file():
                # Skip __pycache__ and migration files
                if '__pycache__' in str(file_path):
                    continue
                if '/migrations/' in str(file_path) and file_path.name != '__init__.py':
                    continue
                    
                self.log(f"Scanning: {file_path}")
                result = self.scan_file(str(file_path))
                results.append(result)
        
        return results
    
    def scan_database_plugins(self) -> List[ScanResult]:
        """Scan CloudBolt plugins stored in the database."""
        results = []
        
        if not DJANGO_AVAILABLE:
            self.log("Django not available, skipping database plugin scan")
            return results
        
        try:
            from cbhooks.models import CloudBoltHook, ServerAction, ResourceAction, SharedModule
            
            # Scan CloudBolt Plugins
            for hook in CloudBoltHook.objects.filter(module_file__isnull=False).exclude(module_file=''):
                if hook.module_file:
                    try:
                        file_path = hook.module_file.path
                        if os.path.exists(file_path):
                            self.log(f"Scanning plugin: {hook.name} ({file_path})")
                            result = self.scan_file(file_path)
                            result.file_path = f"[Plugin: {hook.name}] {file_path}"
                            results.append(result)
                    except Exception as e:
                        self.log(f"Error scanning plugin {hook.name}: {e}")
            
            # Scan Shared Modules
            for module in SharedModule.objects.filter(module_file__isnull=False).exclude(module_file=''):
                if module.module_file:
                    try:
                        file_path = module.module_file.path
                        if os.path.exists(file_path):
                            self.log(f"Scanning shared module: {module.name} ({file_path})")
                            result = self.scan_file(file_path)
                            result.file_path = f"[SharedModule: {module.name}] {file_path}"
                            results.append(result)
                    except Exception as e:
                        self.log(f"Error scanning shared module {module.name}: {e}")
                        
        except Exception as e:
            self.log(f"Error scanning database plugins: {e}")
        
        return results


class ReportGenerator:
    """Generates compatibility reports in various formats."""
    
    def __init__(self, report: CompatibilityReport):
        self.report = report
    
    def to_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(self.report.to_dict(), indent=2, default=str)
    
    def to_text(self) -> str:
        """Generate plain text report."""
        lines = []
        r = self.report
        
        lines.append("=" * 80)
        lines.append("CLOUDBOLT DJANGO 5.2.x / PYTHON 3.12.x COMPATIBILITY REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Scan Date: {r.scan_date}")
        lines.append(f"CloudBolt Version: {r.cloudbolt_version}")
        lines.append(f"Current Django Version: {r.current_django_version}")
        lines.append(f"Current Python Version: {r.current_python_version}")
        lines.append(f"Target Django Version: {r.target_django_version}")
        lines.append(f"Target Python Version: {r.target_python_version}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Files Scanned: {r.total_files_scanned}")
        lines.append(f"Total Issues Found: {r.total_issues}")
        lines.append("")
        lines.append(f"  CRITICAL: {r.critical_count}")
        lines.append(f"  HIGH:     {r.high_count}")
        lines.append(f"  MEDIUM:   {r.medium_count}")
        lines.append(f"  LOW:      {r.low_count}")
        lines.append(f"  INFO:     {r.info_count}")
        lines.append("")
        
        if r.issues_by_type:
            lines.append("-" * 80)
            lines.append("ISSUES BY TYPE")
            lines.append("-" * 80)
            for issue_type, count in sorted(r.issues_by_type.items(), key=lambda x: -x[1]):
                lines.append(f"  {issue_type}: {count}")
            lines.append("")
        
        lines.append("-" * 80)
        lines.append("DETAILED FINDINGS")
        lines.append("-" * 80)
        
        for result in r.scan_results:
            if result.issues or result.error:
                lines.append("")
                lines.append(f"FILE: {result.file_path}")
                if result.error:
                    lines.append(f"  ERROR: {result.error}")
                for issue in result.issues:
                    lines.append(f"  Line {issue.line_number}: [{issue.severity}] {issue.issue_type}")
                    lines.append(f"    Description: {issue.description}")
                    lines.append(f"    Found: {issue.deprecated_code}")
                    lines.append(f"    Fix: {issue.recommended_fix}")
                    if issue.django_version:
                        lines.append(f"    Django: {issue.django_version}")
                    if issue.python_version:
                        lines.append(f"    Python: {issue.python_version}")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """Generate HTML report."""
        r = self.report
        
        # Count issues by severity for each file
        critical_files = []
        high_files = []
        
        for result in r.scan_results:
            has_critical = any(i.severity == 'CRITICAL' for i in result.issues)
            has_high = any(i.severity == 'HIGH' for i in result.issues)
            if has_critical:
                critical_files.append(result.file_path)
            elif has_high:
                high_files.append(result.file_path)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudBolt Compatibility Report</title>
    <style>
        :root {{
            --critical: #dc3545;
            --high: #fd7e14;
            --medium: #ffc107;
            --low: #17a2b8;
            --info: #6c757d;
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --text-primary: #eee;
            --text-secondary: #aaa;
            --border: #0f3460;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{ color: var(--text-secondary); margin-bottom: 2rem; }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .meta-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
        }}
        
        .meta-card label {{
            display: block;
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .meta-card .value {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .severity-card {{
            background: var(--bg-card);
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            border-left: 4px solid;
        }}
        
        .severity-card.critical {{ border-color: var(--critical); }}
        .severity-card.high {{ border-color: var(--high); }}
        .severity-card.medium {{ border-color: var(--medium); }}
        .severity-card.low {{ border-color: var(--low); }}
        .severity-card.info {{ border-color: var(--info); }}
        
        .severity-card .count {{
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1;
        }}
        
        .severity-card.critical .count {{ color: var(--critical); }}
        .severity-card.high .count {{ color: var(--high); }}
        .severity-card.medium .count {{ color: var(--medium); }}
        .severity-card.low .count {{ color: var(--low); }}
        .severity-card.info .count {{ color: var(--info); }}
        
        .severity-card .label {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
        }}
        
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        
        .section-header {{
            background: rgba(255,255,255,0.05);
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }}
        
        .section-content {{ padding: 1.5rem; }}
        
        .issue-list {{ list-style: none; }}
        
        .issue-item {{
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-left: 3px solid;
        }}
        
        .issue-item.CRITICAL {{ border-color: var(--critical); }}
        .issue-item.HIGH {{ border-color: var(--high); }}
        .issue-item.MEDIUM {{ border-color: var(--medium); }}
        .issue-item.LOW {{ border-color: var(--low); }}
        .issue-item.INFO {{ border-color: var(--info); }}
        
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        
        .issue-type {{ font-weight: 600; }}
        
        .badge {{
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        
        .badge.CRITICAL {{ background: var(--critical); }}
        .badge.HIGH {{ background: var(--high); color: #000; }}
        .badge.MEDIUM {{ background: var(--medium); color: #000; }}
        .badge.LOW {{ background: var(--low); }}
        .badge.INFO {{ background: var(--info); }}
        
        .issue-details {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        
        .issue-details p {{ margin: 0.25rem 0; }}
        
        .code {{
            font-family: 'Fira Code', 'Consolas', monospace;
            background: rgba(0,0,0,0.3);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.85rem;
        }}
        
        .fix {{
            color: #4ade80;
            font-style: italic;
        }}
        
        .file-path {{
            word-break: break-all;
            font-family: monospace;
            font-size: 0.9rem;
            color: #60a5fa;
        }}
        
        .collapsible {{
            cursor: pointer;
        }}
        
        .collapsible:after {{
            content: ' ▼';
            font-size: 0.7rem;
        }}
        
        .issues-by-type {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 0.5rem;
        }}
        
        .type-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
        }}
        
        .no-issues {{
            text-align: center;
            padding: 3rem;
            color: #4ade80;
            font-size: 1.2rem;
        }}
        
        @media (max-width: 768px) {{
            .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .meta-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 CloudBolt Compatibility Report</h1>
        <p class="subtitle">Django 5.2.x & Python 3.12.x Readiness Assessment</p>
        
        <div class="meta-grid">
            <div class="meta-card">
                <label>Scan Date</label>
                <div class="value">{r.scan_date}</div>
            </div>
            <div class="meta-card">
                <label>CloudBolt Version</label>
                <div class="value">{r.cloudbolt_version}</div>
            </div>
            <div class="meta-card">
                <label>Current Django</label>
                <div class="value">{r.current_django_version}</div>
            </div>
            <div class="meta-card">
                <label>Current Python</label>
                <div class="value">{r.current_python_version}</div>
            </div>
            <div class="meta-card">
                <label>Target Django</label>
                <div class="value">{r.target_django_version}</div>
            </div>
            <div class="meta-card">
                <label>Target Python</label>
                <div class="value">{r.target_python_version}</div>
            </div>
            <div class="meta-card">
                <label>Files Scanned</label>
                <div class="value">{r.total_files_scanned}</div>
            </div>
            <div class="meta-card">
                <label>Total Issues</label>
                <div class="value">{r.total_issues}</div>
            </div>
        </div>
        
        <div class="summary-grid">
            <div class="severity-card critical">
                <div class="count">{r.critical_count}</div>
                <div class="label">Critical</div>
            </div>
            <div class="severity-card high">
                <div class="count">{r.high_count}</div>
                <div class="label">High</div>
            </div>
            <div class="severity-card medium">
                <div class="count">{r.medium_count}</div>
                <div class="label">Medium</div>
            </div>
            <div class="severity-card low">
                <div class="count">{r.low_count}</div>
                <div class="label">Low</div>
            </div>
            <div class="severity-card info">
                <div class="count">{r.info_count}</div>
                <div class="label">Info</div>
            </div>
        </div>
'''
        
        # Issues by type section
        if r.issues_by_type:
            html += '''
        <div class="section">
            <div class="section-header">📊 Issues by Type</div>
            <div class="section-content">
                <div class="issues-by-type">
'''
            for issue_type, count in sorted(r.issues_by_type.items(), key=lambda x: -x[1]):
                html += f'''                    <div class="type-item">
                        <span>{issue_type}</span>
                        <span><strong>{count}</strong></span>
                    </div>
'''
            html += '''                </div>
            </div>
        </div>
'''
        
        # Detailed findings
        files_with_issues = [res for res in r.scan_results if res.issues or res.error]
        
        if files_with_issues:
            html += '''
        <div class="section">
            <div class="section-header">📁 Detailed Findings</div>
            <div class="section-content">
'''
            for result in files_with_issues:
                html += f'''
                <div style="margin-bottom: 2rem;">
                    <div class="file-path" style="margin-bottom: 0.5rem;">{result.file_path}</div>
'''
                if result.error:
                    html += f'                    <p style="color: var(--critical);">Error: {result.error}</p>\n'
                
                if result.issues:
                    html += '                    <ul class="issue-list">\n'
                    for issue in result.issues:
                        html += f'''                        <li class="issue-item {issue.severity}">
                            <div class="issue-header">
                                <span class="issue-type">{issue.issue_type}</span>
                                <span class="badge {issue.severity}">{issue.severity}</span>
                            </div>
                            <div class="issue-details">
                                <p><strong>Line {issue.line_number}:</strong> {issue.description}</p>
                                <p>Found: <code class="code">{issue.deprecated_code}</code></p>
                                <p class="fix">💡 Fix: {issue.recommended_fix}</p>
'''
                        if issue.django_version:
                            html += f'                                <p><small>Django: {issue.django_version}</small></p>\n'
                        if issue.python_version:
                            html += f'                                <p><small>Python: {issue.python_version}</small></p>\n'
                        html += '''                            </div>
                        </li>
'''
                    html += '                    </ul>\n'
                html += '                </div>\n'
            
            html += '''            </div>
        </div>
'''
        else:
            html += '''
        <div class="section">
            <div class="section-content no-issues">
                ✅ No compatibility issues found! Your code is ready for Django 5.2.x and Python 3.12.x
            </div>
        </div>
'''
        
        html += '''
    </div>
</body>
</html>
'''
        return html


def get_version_info() -> Tuple[str, str, str]:
    """Get CloudBolt, Django, and Python version info."""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    django_version = "Unknown"
    cloudbolt_version = "Unknown"
    
    # Try to get versions from Django settings
    if DJANGO_AVAILABLE:
        try:
            import django
            django_version = django.get_version()
        except Exception:
            pass
        
        try:
            from django.conf import settings
            cloudbolt_version = settings.VERSION_INFO.get('VERSION', 'Unknown')
        except Exception:
            pass
    
    # If CloudBolt version not found via Django, read directly from settings.py
    if cloudbolt_version == "Unknown":
        settings_paths = [
            '/opt/cloudbolt/settings.py',
            os.path.join(CB_ROOT, 'settings.py'),
        ]
        for settings_path in settings_paths:
            if os.path.isfile(settings_path):
                try:
                    with open(settings_path, 'r') as f:
                        content = f.read()
                    # Parse VERSION_INFO dict
                    version_match = re.search(r'VERSION_INFO\s*=\s*\{[^}]*"VERSION"\s*:\s*"([^"]+)"', content)
                    build_match = re.search(r'VERSION_INFO\s*=\s*\{[^}]*"BUILD"\s*:\s*"([^"]+)"', content)
                    if version_match:
                        version = version_match.group(1)
                        build = build_match.group(1) if build_match else ""
                        cloudbolt_version = f"{version} ({build})" if build else version
                        break
                except Exception:
                    pass
    
    # If Django version not found, try to read from installed packages
    if django_version == "Unknown":
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, '-c', 'import django; print(django.get_version())'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                django_version = result.stdout.strip()
        except Exception:
            pass
    
    return cloudbolt_version, django_version, python_version


def main():
    parser = argparse.ArgumentParser(
        description='Scan CloudBolt customer code for Django 5.2.x and Python 3.12.x compatibility issues'
    )
    parser.add_argument(
        '--output-format', 
        choices=['json', 'html', 'text'], 
        default='text',
        help='Output format for the report (default: text)'
    )
    parser.add_argument(
        '--output-file',
        help='Output file path (default: stdout for text, compatibility_report.html/json for others)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--scan-database',
        action='store_true',
        default=True,
        help='Scan plugins stored in database (default: True)'
    )
    parser.add_argument(
        '--additional-paths',
        nargs='*',
        help='Additional paths to scan'
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = CompatibilityScanner(verbose=args.verbose)
    
    # Get version info
    cloudbolt_version, django_version, python_version = get_version_info()
    
    print("=" * 60)
    print("CloudBolt Django 5.2.x / Python 3.12.x Compatibility Scanner")
    print("=" * 60)
    print(f"CloudBolt Version: {cloudbolt_version}")
    print(f"Current Django: {django_version}")
    print(f"Current Python: {python_version}")
    print(f"Target Django: 5.2.x")
    print(f"Target Python: 3.12.x")
    print("=" * 60)
    print()
    
    all_results = []
    
    # Standard customer directories to scan
    customer_directories = [
        '/var/opt/cloudbolt/proserv/',
        '/var/www/html/cloudbolt/static/uploads/hooks/',
        '/var/www/html/cloudbolt/static/uploads/shared_modules/',
    ]
    
    # Add additional paths if specified
    if args.additional_paths:
        customer_directories.extend(args.additional_paths)
    
    # Scan directories
    for directory in customer_directories:
        print(f"Scanning directory: {directory}")
        results = scanner.scan_directory(directory)
        all_results.extend(results)
        issues_count = sum(len(r.issues) for r in results)
        print(f"  Found {len(results)} files, {issues_count} issues")
    
    # Scan database plugins
    if args.scan_database:
        print("\nScanning database plugins...")
        db_results = scanner.scan_database_plugins()
        all_results.extend(db_results)
        issues_count = sum(len(r.issues) for r in db_results)
        print(f"  Found {len(db_results)} plugins, {issues_count} issues")
    
    print()
    
    # Calculate statistics
    total_issues = sum(len(r.issues) for r in all_results)
    critical_count = sum(1 for r in all_results for i in r.issues if i.severity == 'CRITICAL')
    high_count = sum(1 for r in all_results for i in r.issues if i.severity == 'HIGH')
    medium_count = sum(1 for r in all_results for i in r.issues if i.severity == 'MEDIUM')
    low_count = sum(1 for r in all_results for i in r.issues if i.severity == 'LOW')
    info_count = sum(1 for r in all_results for i in r.issues if i.severity == 'INFO')
    
    issues_by_type = defaultdict(int)
    for result in all_results:
        for issue in result.issues:
            issues_by_type[issue.issue_type] += 1
    
    # Create report
    report = CompatibilityReport(
        scan_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        cloudbolt_version=cloudbolt_version,
        current_django_version=django_version,
        current_python_version=python_version,
        target_django_version='5.2.x',
        target_python_version='3.12.x',
        total_files_scanned=len(all_results),
        total_issues=total_issues,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        info_count=info_count,
        issues_by_type=dict(issues_by_type),
        scan_results=all_results,
    )
    
    # Generate report
    generator = ReportGenerator(report)
    
    # Default output directory
    output_dir = '/var/tmp'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if args.output_format == 'json':
        output = generator.to_json()
        default_file = f'{output_dir}/cloudbolt_compatibility_report_{timestamp}.json'
    elif args.output_format == 'html':
        output = generator.to_html()
        default_file = f'{output_dir}/cloudbolt_compatibility_report_{timestamp}.html'
    else:
        output = generator.to_text()
        default_file = f'{output_dir}/cloudbolt_compatibility_report_{timestamp}.txt'
    
    # Write output
    output_file = args.output_file or default_file
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report written to: {output_file}")
    else:
        print(output)
    
    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Files Scanned: {len(all_results)}")
    print(f"Total Issues Found: {total_issues}")
    print(f"  CRITICAL: {critical_count}")
    print(f"  HIGH:     {high_count}")
    print(f"  MEDIUM:   {medium_count}")
    print(f"  LOW:      {low_count}")
    print(f"  INFO:     {info_count}")
    print()
    
    if critical_count > 0:
        print("⚠️  CRITICAL issues found! These MUST be fixed before upgrading.")
        sys.exit(1)
    elif high_count > 0:
        print("⚠️  HIGH priority issues found. These should be fixed before upgrading.")
        sys.exit(0)
    else:
        print("✅ No critical issues found. Review medium/low priority items as needed.")
        sys.exit(0)


if __name__ == '__main__':
    main()

