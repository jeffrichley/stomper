#!/usr/bin/env python3
"""Test integration between quality tools and cursor client."""

import tempfile
from pathlib import Path
from src.stomper.quality.manager import QualityToolManager
from src.stomper.ai.sandbox_manager import SandboxManager
from src.stomper.ai.cursor_client import CursorClient
from dotenv import load_dotenv
import os

load_dotenv()

# Print the CURSOR_API_KEY to verify it's loaded
print(f"CURSOR_API_KEY: {os.getenv('CURSOR_API_KEY', 'NOT SET')}")


def create_test_project_with_errors(temp_dir: Path) -> None:
    """Create a test project with actual linting errors."""
    
    # Create a Python file with real linting errors
    test_file = temp_dir / "bad_code.py"
    test_file.write_text('''#!/usr/bin/env python3
"""Test file with real linting errors."""

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
    very_long_variable_name_that_should_trigger_line_length_error = "This is a very long string that makes this line exceed the typical 88 character limit"
    
    # Unused import simulation
    unused_var = "This variable is never used"
    
    return very_long_variable_name_that_should_trigger_line_length_error

class BadClass:
    # Missing docstring
    def __init__(self):
        self.value = None
    
    def method_with_issues(self):
        # Missing docstring
        if True:
            pass
        else:
            pass

if __name__ == "__main__":
    # This will have issues
    result = bad_function()
    print(f"Bad result: {result}")
''')
    
    # Create a pyproject.toml with ruff config
    (temp_dir / "pyproject.toml").write_text('''[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = ["E", "F", "W", "C90", "I", "N", "UP", "YTT", "S", "BLE", "FBT", "B", "A", "COM", "C4", "DTZ", "T10", "EM", "EXE", "FA", "ISC", "ICN", "G", "INP", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SIM", "TID", "TCH", "INT", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "FLY", "NPY", "AIR", "PERF", "FURB", "LOG", "RUF"]
ignore = []

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
''')
    
    # Initialize git repo
    from git import Repo
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Add and commit initial files
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit with linting errors")


def test_quality_tools_integration():
    """Test the full integration: quality tools → cursor client → fixes."""
    print("=" * 60)
    print("TESTING QUALITY TOOLS + CURSOR CLIENT INTEGRATION")
    print("=" * 60)
    
    # Create test project with real errors
    temp_dir = Path(tempfile.mkdtemp(prefix="test_quality_integration_"))
    print(f"Created test project: {temp_dir}")
    
    try:
        # Create project with real linting errors
        create_test_project_with_errors(temp_dir)
        print("✅ Created test project with linting errors")
        
        # Step 1: Run quality tools to find errors
        print("\n🔍 Step 1: Running quality tools...")
        quality_manager = QualityToolManager()
        
        # Run ruff to find errors
        errors = quality_manager.run_tools(
            target_path=temp_dir,
            project_root=temp_dir,
            enabled_tools=["ruff"],
            max_errors=50
        )
        
        print(f"Found {len(errors)} errors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  {error.file.name}:{error.line} - {error.code}: {error.message}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
        
        if not errors:
            print("❌ No errors found - cannot test fixing")
            return
        
        # Step 2: Group errors by file
        print(f"\n📁 Step 2: Grouping errors by file...")
        errors_by_file = {}
        for error in errors:
            file_path = error.file
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)
        
        print(f"Errors found in {len(errors_by_file)} files:")
        for file_path, file_errors in errors_by_file.items():
            print(f"  {file_path.name}: {len(file_errors)} errors")
        
        # Step 3: Create sandbox and cursor client
        print(f"\n🏗️ Step 3: Setting up sandbox and cursor client...")
        sandbox_manager = SandboxManager(temp_dir)
        cursor_client = CursorClient(sandbox_manager)
        
        print(f"✅ Cursor client available: {cursor_client.is_available()}")
        
        # Create sandbox
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        print(f"✅ Created sandbox: {sandbox_path}")
        
        # Step 4: Fix each file with errors
        print(f"\n🤖 Step 4: Fixing files with cursor-agent...")
        
        for file_path, file_errors in errors_by_file.items():
            print(f"\n📄 Fixing {file_path.name} ({len(file_errors)} errors)...")
            
            # Create a targeted prompt based on the errors
            error_summary = []
            for error in file_errors[:10]:  # Limit to first 10 errors
                error_summary.append(f"- Line {error.line}: {error.code} - {error.message}")
            
            prompt = f"""Fix all the linting errors in this Python file.

Specific errors to fix:
{chr(10).join(error_summary)}

Please fix all these issues while maintaining the functionality of the code.
After fixing, the code should pass all linting checks.
Once finished, print 'Done fixing {file_path.name}!' and exit.
"""
            
            print(f"Prompt: {prompt[:100]}...")
            
            try:
                # Run cursor client on this file
                result = cursor_client.generate_fix(prompt, sandbox_path)
                
                print(f"✅ Cursor-agent completed for {file_path.name}")
                print(f"  Return code: {result['execution_result']['returncode']}")
                print(f"  Events: {len(result['execution_result']['events'])}")
                print(f"  Files modified: {result['sandbox_status']['modified']}")
                
            except Exception as e:
                print(f"❌ Error fixing {file_path.name}: {e}")
        
        # Step 5: Check if errors were fixed
        print(f"\n🔍 Step 5: Checking if errors were fixed...")
        
        # Run quality tools again on the sandbox
        sandbox_errors = quality_manager.run_tools(
            target_path=sandbox_path,
            project_root=sandbox_path,
            enabled_tools=["ruff"],
            max_errors=50
        )
        
        print(f"Found {len(sandbox_errors)} errors after fixing:")
        if sandbox_errors:
            for error in sandbox_errors[:5]:  # Show first 5 errors
                print(f"  {error.file.name}:{error.line} - {error.code}: {error.message}")
            if len(sandbox_errors) > 5:
                print(f"  ... and {len(sandbox_errors) - 5} more errors")
        else:
            print("  🎉 No errors found! All issues were fixed!")
        
        # Step 6: Show the diff
        print(f"\n📋 Step 6: Getting diff...")
        diff = sandbox_manager.get_sandbox_diff(sandbox_path)
        if diff:
            print(f"Diff length: {len(diff)} characters")
            print(f"First 500 characters of diff:")
            print("-" * 50)
            print(diff[:500])
            if len(diff) > 500:
                print("...")
        else:
            print("No diff found")
        
        # Step 7: Show some of the fixed code
        if (sandbox_path / "bad_code.py").exists():
            print(f"\n📄 Fixed code preview:")
            print("-" * 50)
            fixed_code = (sandbox_path / "bad_code.py").read_text()
            print(fixed_code[:500])
            if len(fixed_code) > 500:
                print("...")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  Original errors: {len(errors)}")
        print(f"  Errors after fixing: {len(sandbox_errors)}")
        print(f"  Errors fixed: {len(errors) - len(sandbox_errors)}")
        print(f"  Success rate: {((len(errors) - len(sandbox_errors)) / len(errors) * 100):.1f}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
        except:
            pass
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up: {temp_dir}")


if __name__ == "__main__":
    test_quality_tools_integration()
