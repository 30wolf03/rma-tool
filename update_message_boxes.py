#!/usr/bin/env python3
"""Script to update all QMessageBox calls to use enhanced logging.

This script automatically replaces QMessageBox calls with the enhanced
logging system throughout the project.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_python_files(directory: str) -> List[str]:
    """Find all Python files in the given directory.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of Python file paths
    """
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip venv and __pycache__ directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files


def update_file_imports(file_path: str) -> bool:
    """Update imports in a file to include enhanced logging.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        True if file was modified, False otherwise
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Add import for enhanced logging if QMessageBox is used
    if 'QMessageBox' in content and 'enhanced_logging' not in content:
        # Find the import section
        import_pattern = r'(from PyQt6\.QtWidgets import.*?QMessageBox.*?)(\n)'
        match = re.search(import_pattern, content, re.DOTALL)
        
        if match:
            # Add enhanced logging import
            enhanced_import = '\nfrom shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog\n'
            content = content.replace(match.group(1), match.group(1) + enhanced_import)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False


def update_qmessagebox_calls(file_path: str) -> Tuple[int, int]:
    """Update QMessageBox calls in a file.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        Tuple of (critical_count, warning_count, info_count)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    critical_count = 0
    warning_count = 0
    info_count = 0
    
    # Pattern for QMessageBox.critical calls
    critical_pattern = r'QMessageBox\.critical\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'
    
    def critical_replacement(match):
        nonlocal critical_count
        critical_count += 1
        parent = match.group(1).strip()
        title = match.group(2).strip()
        message = match.group(3).strip()
        
        # If parent is 'self', use 'self', otherwise use 'None'
        parent_arg = 'self' if 'self' in parent else 'None'
        
        return f'LoggingMessageBox.critical({parent_arg}, {title}, {message})'
    
    content = re.sub(critical_pattern, critical_replacement, content)
    
    # Pattern for QMessageBox.warning calls
    warning_pattern = r'QMessageBox\.warning\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'
    
    def warning_replacement(match):
        nonlocal warning_count
        warning_count += 1
        parent = match.group(1).strip()
        title = match.group(2).strip()
        message = match.group(3).strip()
        
        parent_arg = 'self' if 'self' in parent else 'None'
        
        return f'LoggingMessageBox.warning({parent_arg}, {title}, {message})'
    
    content = re.sub(warning_pattern, warning_replacement, content)
    
    # Pattern for QMessageBox.information calls
    info_pattern = r'QMessageBox\.information\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'
    
    def info_replacement(match):
        nonlocal info_count
        info_count += 1
        parent = match.group(1).strip()
        title = match.group(2).strip()
        message = match.group(3).strip()
        
        parent_arg = 'self' if 'self' in parent else 'None'
        
        return f'LoggingMessageBox.information({parent_arg}, {title}, {message})'
    
    content = re.sub(info_pattern, info_replacement, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return critical_count, warning_count, info_count


def main():
    """Main function to update all QMessageBox calls."""
    print("Updating QMessageBox calls to use enhanced logging...")
    
    # Find all Python files
    python_files = find_python_files('.')
    
    total_critical = 0
    total_warning = 0
    total_info = 0
    modified_files = 0
    
    for file_path in python_files:
        print(f"Processing: {file_path}")
        
        # Update imports
        imports_modified = update_file_imports(file_path)
        
        # Update QMessageBox calls
        critical, warning, info = update_qmessagebox_calls(file_path)
        
        if critical > 0 or warning > 0 or info > 0 or imports_modified:
            modified_files += 1
            print(f"  - Critical: {critical}, Warning: {warning}, Info: {info}")
        
        total_critical += critical
        total_warning += warning
        total_info += info
    
    print(f"\nSummary:")
    print(f"  - Modified files: {modified_files}")
    print(f"  - Total critical calls: {total_critical}")
    print(f"  - Total warning calls: {total_warning}")
    print(f"  - Total info calls: {total_info}")
    print(f"  - Total QMessageBox calls updated: {total_critical + total_warning + total_info}")


if __name__ == "__main__":
    main() 