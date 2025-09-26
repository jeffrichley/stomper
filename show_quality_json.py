#!/usr/bin/env python3
"""Show raw JSON output from quality tools."""

import json
import tempfile
from pathlib import Path
from src.stomper.quality.manager import QualityToolManager

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

# MyPy type errors
def type_error_function(x: str) -> int:
    return x + 1  # MyPy error: unsupported operand type(s) for +: 'str' and 'int'

def missing_type_annotation(value):
    return value.upper()  # MyPy error: missing type annotation

def wrong_return_type() -> str:
    return 42  # MyPy error: returning int but expecting str

# More type issues
def list_type_error():
    items = [1, 2, 3]
    return items[0] + "hello"  # MyPy error: unsupported operand types

def optional_type_error(value: str = None):
    return value.upper()  # MyPy error: value could be None
''')
        
        print("🔍 Running quality tools on test file...")
        print(f"Test file: {test_file}")
        print()
        
        # Initialize quality manager
        quality_manager = QualityToolManager()
        
        # Run quality tools
        print("📊 Quality Tools Results:")
        print("=" * 50)
        
        # Get all errors
        all_errors = quality_manager.run_tools(
            target_path=test_file,
            project_root=temp_path,
            enabled_tools=["ruff", "mypy"]
        )
        
        print(f"Total errors found: {len(all_errors)}")
        print()
        
        # Show JSON representation of errors
        print("📋 JSON Output (first 5 errors):")
        print("=" * 50)
        
        for i, error in enumerate(all_errors):
            print(f"Error {i+1}:")
            error_dict = {
                "file": str(error.file),
                "line": error.line,
                "column": error.column,
                "code": error.code,
                "message": error.message,
                "tool": error.tool
            }
            # print(json.dumps(error_dict, indent=2))
            # print()
            print(error.model_dump_json(indent=2))

        print("=" * 50)
        print("📊 Summary:")
        print(f"  Total errors: {len(all_errors)}")
        
        # Group by tool
        by_tool = {}
        for error in all_errors:
            by_tool[error.tool] = by_tool.get(error.tool, 0) + 1
        
        print("  By tool:")
        for tool, count in by_tool.items():
            print(f"    {tool}: {count} errors")
        
        # Group by file
        by_file = {}
        for error in all_errors:
            by_file[str(error.file)] = by_file.get(str(error.file), 0) + 1
        
        print("  By file:")
        for file, count in by_file.items():
            print(f"    {file}: {count} errors")

if __name__ == "__main__":
    main()
