#!/usr/bin/env python3
"""Show raw JSON output from individual quality tools."""

import json
import subprocess
import tempfile
from pathlib import Path

def main():
    # Create a temporary test file with errors
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a Python file with various linting errors
        test_file = temp_path / "test_errors.py"
        test_file.write_text('''#!/usr/bin/env python3
"""Test file with various linting errors."""

import os
import sys
import json

def bad_function():
    # Missing docstring
    x = 1
    y = 2
    z = x + y
    print(f"Result: {z}")
    return z

def another_bad_function():
    # Line too long - this line is way too long and should trigger E501 line length error in ruff
    very_long_variable_name_that_should_trigger_line_length_error = "This is a very long string that makes this line exceed the maximum line length limit"
    return very_long_variable_name_that_should_trigger_line_length_error

class BadClass:
    # Missing docstring
    def __init__(self):
        self.value = None
    
    def method_without_docstring(self):
        return self.value
''')
        
        print("🔍 Raw JSON Output from Quality Tools")
        print("=" * 60)
        print(f"Test file: {test_file}")
        print()
        
        # Test Ruff JSON output
        print("📋 RUFF JSON OUTPUT:")
        print("-" * 40)
        try:
            ruff_cmd = ["ruff", "check", "--output-format=json", str(test_file)]
            result = subprocess.run(ruff_cmd, capture_output=True, text=True, cwd=temp_path)
            
            if result.returncode == 0:
                print("No Ruff errors found")
            else:
                print("Raw Ruff JSON output:")
                print(result.stdout)
                
                # Parse and pretty print
                try:
                    ruff_data = json.loads(result.stdout)
                    print("\nParsed Ruff JSON:")
                    print(json.dumps(ruff_data, indent=2))
                except json.JSONDecodeError:
                    print("Could not parse as JSON")
                    
        except FileNotFoundError:
            print("Ruff not found in PATH")
        
        print("\n" + "=" * 60)
        
        # Test MyPy JSON output
        print("📋 MYPY JSON OUTPUT:")
        print("-" * 40)
        try:
            mypy_cmd = ["mypy", "--json-report", "/tmp/mypy_report.json", str(test_file)]
            result = subprocess.run(mypy_cmd, capture_output=True, text=True, cwd=temp_path)
            
            # MyPy writes to a file, so read it
            report_file = Path("/tmp/mypy_report.json")
            if report_file.exists():
                with open(report_file, 'r') as f:
                    mypy_data = json.load(f)
                
                print("Raw MyPy JSON output:")
                print(json.dumps(mypy_data, indent=2))
            else:
                print("MyPy report file not found")
                print("MyPy stdout:", result.stdout)
                print("MyPy stderr:", result.stderr)
                
        except FileNotFoundError:
            print("MyPy not found in PATH")
        
        print("\n" + "=" * 60)
        
        # Test Drill Sergeant JSON output
        print("📋 DRILL SERGEANT JSON OUTPUT:")
        print("-" * 40)
        try:
            drill_cmd = ["drill-sergeant", "--format", "json", str(test_file)]
            result = subprocess.run(drill_cmd, capture_output=True, text=True, cwd=temp_path)
            
            if result.returncode == 0:
                print("No Drill Sergeant errors found")
            else:
                print("Raw Drill Sergeant JSON output:")
                print(result.stdout)
                
                # Parse and pretty print
                try:
                    drill_data = json.loads(result.stdout)
                    print("\nParsed Drill Sergeant JSON:")
                    print(json.dumps(drill_data, indent=2))
                except json.JSONDecodeError:
                    print("Could not parse as JSON")
                    
        except FileNotFoundError:
            print("Drill Sergeant not found in PATH")

if __name__ == "__main__":
    main()