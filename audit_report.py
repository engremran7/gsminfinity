#!/usr/bin/env python3
"""
Comprehensive Repository Audit Script
Analyzes Django apps for common issues and generates a report
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def count_lines_of_code(directory):
    """Count lines of Python code in directory"""
    total = 0
    for path in Path(directory).rglob("*.py"):
        if "migrations" not in str(path) and "__pycache__" not in str(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    total += len([l for l in f if l.strip() and not l.strip().startswith('#')])
            except:
                pass
    return total

def check_models_have_str(models_file):
    """Check if all models have __str__ method"""
    if not os.path.exists(models_file):
        return []
    
    issues = []
    try:
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find all class definitions that inherit from models.Model
            model_pattern = r'class\s+(\w+)\((.*models\.Model.*)\):'
            models_found = re.findall(model_pattern, content)
            
            for model_name, _ in models_found:
                # Check if there's a __str__ method for this model
                str_pattern = rf'class\s+{model_name}.*?(?=class\s|\Z)'
                match = re.search(str_pattern, content, re.DOTALL)
                if match and 'def __str__' not in match.group(0):
                    issues.append(f"Model {model_name} missing __str__ method")
    except Exception as e:
        issues.append(f"Error checking models: {e}")
    
    return issues

def check_urls_have_names(urls_file):
    """Check if URL patterns have names"""
    if not os.path.exists(urls_file):
        return []
    
    issues = []
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find path() calls without name parameter
            unnamed_patterns = re.findall(r'path\([^)]+\)(?!\s*,\s*name\s*=)', content)
            if unnamed_patterns:
                issues.append(f"Found {len(unnamed_patterns)} URL patterns without names")
    except Exception as e:
        issues.append(f"Error checking URLs: {e}")
    
    return issues

def check_tests_exist(test_file):
    """Check if tests exist"""
    return os.path.exists(test_file) and os.path.getsize(test_file) > 100

def analyze_app(app_path):
    """Analyze a single Django app"""
    app_name = os.path.basename(app_path)
    results = {
        'name': app_name,
        'loc': count_lines_of_code(app_path),
        'has_models': os.path.exists(os.path.join(app_path, 'models.py')),
        'has_views': os.path.exists(os.path.join(app_path, 'views.py')),
        'has_urls': os.path.exists(os.path.join(app_path, 'urls.py')),
        'has_admin': os.path.exists(os.path.join(app_path, 'admin.py')),
        'has_tests': check_tests_exist(os.path.join(app_path, 'tests.py')),
        'has_api': os.path.exists(os.path.join(app_path, 'api.py')),
        'has_services': os.path.exists(os.path.join(app_path, 'services.py')) or os.path.exists(os.path.join(app_path, 'services')),
        'model_issues': check_models_have_str(os.path.join(app_path, 'models.py')),
        'url_issues': check_urls_have_names(os.path.join(app_path, 'urls.py')),
    }
    return results

def generate_report():
    """Generate comprehensive audit report"""
    base_dir = Path(__file__).parent
    apps_dir = base_dir / 'apps'
    
    if not apps_dir.exists():
        print("Apps directory not found!")
        return
    
    print("=" * 80)
    print("DJANGO WEB APPLICATION AUDIT REPORT")
    print("=" * 80)
    print()
    
    # Analyze all apps
    apps = []
    total_loc = 0
    apps_with_tests = 0
    apps_with_models = 0
    apps_with_services = 0
    
    for app_dir in sorted(apps_dir.iterdir()):
        if app_dir.is_dir() and not app_dir.name.startswith('__'):
            result = analyze_app(app_dir)
            apps.append(result)
            total_loc += result['loc']
            if result['has_tests']:
                apps_with_tests += 1
            if result['has_models']:
                apps_with_models += 1
            if result['has_services']:
                apps_with_services += 1
    
    # Summary
    print(f"Total Applications: {len(apps)}")
    print(f"Total Lines of Code: {total_loc:,}")
    print(f"Apps with Tests: {apps_with_tests}/{len(apps)} ({apps_with_tests/len(apps)*100:.1f}%)")
    print(f"Apps with Models: {apps_with_models}/{len(apps)}")
    print(f"Apps with Service Layer: {apps_with_services}/{len(apps)}")
    print()
    
    # Detailed app analysis
    print("=" * 80)
    print("APP-BY-APP ANALYSIS")
    print("=" * 80)
    print()
    
    for app in sorted(apps, key=lambda x: x['loc'], reverse=True):
        print(f"\n{app['name'].upper()}")
        print("-" * 40)
        print(f"  Lines of Code: {app['loc']:,}")
        print(f"  Has Models: {'✓' if app['has_models'] else '✗'}")
        print(f"  Has Views: {'✓' if app['has_views'] else '✗'}")
        print(f"  Has URLs: {'✓' if app['has_urls'] else '✗'}")
        print(f"  Has Admin: {'✓' if app['has_admin'] else '✗'}")
        print(f"  Has API: {'✓' if app['has_api'] else '✗'}")
        print(f"  Has Services: {'✓' if app['has_services'] else '✗'}")
        print(f"  Has Tests: {'✓' if app['has_tests'] else '✗'}")
        
        if app['model_issues']:
            print(f"  Model Issues: {len(app['model_issues'])}")
            for issue in app['model_issues'][:3]:  # Show first 3
                print(f"    - {issue}")
        
        if app['url_issues']:
            print(f"  URL Issues:")
            for issue in app['url_issues']:
                print(f"    - {issue}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    apps_needing_tests = [app['name'] for app in apps if not app['has_tests']]
    if apps_needing_tests:
        print("Apps that need tests:")
        for app_name in apps_needing_tests:
            print(f"  - {app_name}")
        print()
    
    apps_without_services = [app['name'] for app in apps if app['has_models'] and not app['has_services']]
    if apps_without_services:
        print("Apps that could benefit from service layer:")
        for app_name in apps_without_services:
            print(f"  - {app_name}")
        print()
    
    large_apps = [app for app in apps if app['loc'] > 1000]
    if large_apps:
        print("Large apps that may need refactoring:")
        for app in large_apps:
            print(f"  - {app['name']}: {app['loc']:,} LOC")
        print()
    
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    generate_report()
