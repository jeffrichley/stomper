#!/usr/bin/env python3
"""Test cursor client with real worktree and actual linting errors."""

import tempfile
import subprocess
from pathlib import Path
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
    
    # Create a requirements.txt
    (temp_dir / "requirements.txt").write_text("requests==2.31.0\npydantic==2.0.0\n")
    
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


def run_ruff_on_project(project_path: Path) -> list:
    """Run ruff on the project and return errors."""
    try:
        result = subprocess.run(
            ["ruff", "check", str(project_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return []
        
        # Parse ruff output
        errors = []
        for line in result.stdout.split('\n'):
            if line.strip() and ':' in line:
                parts = line.split(':')
                if len(parts) >= 4:
                    file_path = parts[0]
                    line_num = parts[1]
                    col_num = parts[2]
                    error_code = parts[3].split()[0] if parts[3].split() else "UNKNOWN"
                    error_msg = ' '.join(parts[3].split()[1:]) if len(parts[3].split()) > 1 else parts[3]
                    
                    errors.append({
                        'file': file_path,
                        'line': int(line_num),
                        'column': int(col_num),
                        'code': error_code,
                        'message': error_msg,
                        'full_line': line
                    })
        
        return errors
        
    except subprocess.TimeoutExpired:
        print("Ruff timed out")
        return []
    except Exception as e:
        print(f"Error running ruff: {e}")
        return []


def test_real_worktree_fixing():
    """Test cursor client with real worktree and actual errors."""
    print("=" * 60)
    print("TESTING REAL WORKTREE FIXING")
    print("=" * 60)
    
    # Create test project with real errors
    temp_dir = Path(tempfile.mkdtemp(prefix="test_real_worktree_"))
    print(f"Created test project: {temp_dir}")
    
    try:
        # Create project with real linting errors
        create_test_project_with_errors(temp_dir)
        print("✅ Created test project with linting errors")
        
        # Run ruff to see initial errors
        print("\n🔍 Running ruff on original project...")
        initial_errors = run_ruff_on_project(temp_dir)
        print(f"Found {len(initial_errors)} initial errors:")
        for error in initial_errors[:5]:  # Show first 5 errors
            print(f"  {error['file']}:{error['line']} - {error['code']}: {error['message']}")
        if len(initial_errors) > 5:
            print(f"  ... and {len(initial_errors) - 5} more errors")
        
        # Create sandbox manager and cursor client
        sandbox_manager = SandboxManager(temp_dir)
        cursor_client = CursorClient(sandbox_manager)
        
        print(f"\n✅ Cursor client available: {cursor_client.is_available()}")
        
        # Create sandbox
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        print(f"✅ Created sandbox: {sandbox_path}")
        
        # Run ruff on sandbox to confirm errors exist
        print("\n🔍 Running ruff on sandbox...")
        sandbox_errors = run_ruff_on_project(sandbox_path)
        print(f"Found {len(sandbox_errors)} errors in sandbox")
        
        # Create a comprehensive prompt for fixing
        prompt = f"""Fix all the linting errors in this Python project. 

The main issues to fix are:
- Line length violations (E501)
- Missing docstrings (D100, D101, D102, D103)
- Unused variables (F841)
- Import organization issues
- Code style violations

Please fix all these issues while maintaining the functionality of the code.
After fixing, run 'ruff check' to verify all issues are resolved.
Once finished, print 'Done fixing!' and exit.
"""
        
        print(f"\n🤖 Running cursor-agent with prompt...")
        print(f"Prompt: {prompt[:100]}...")
        
        # Run the cursor client
        result = cursor_client.generate_fix(prompt, sandbox_path)
        
        print("\n" + "=" * 50)
        print("CURSOR-AGENT RESULTS:")
        print("=" * 50)
        print(f"Return code: {result['execution_result']['returncode']}")
        print(f"Events captured: {len(result['execution_result']['events'])}")
        print(f"Sandbox status: {result['sandbox_status']}")
        
        # Check if files were modified
        if result['sandbox_status']['modified'] or result['sandbox_status']['added']:
            print(f"\n✅ Files were modified!")
            print(f"Modified: {result['sandbox_status']['modified']}")
            print(f"Added: {result['sandbox_status']['added']}")
        else:
            print(f"\n⚠️ No files were modified")
        
        # Run ruff again to see if errors were fixed
        print(f"\n🔍 Running ruff on sandbox after fixing...")
        final_errors = run_ruff_on_project(sandbox_path)
        print(f"Found {len(final_errors)} errors after fixing:")
        
        if final_errors:
            for error in final_errors[:5]:  # Show first 5 errors
                print(f"  {error['file']}:{error['line']} - {error['code']}: {error['message']}")
            if len(final_errors) > 5:
                print(f"  ... and {len(final_errors) - 5} more errors")
        else:
            print("  🎉 No errors found! All issues were fixed!")
        
        # Show the diff
        print(f"\n📋 Getting diff...")
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
        
        # Show some of the fixed code
        if (sandbox_path / "bad_code.py").exists():
            print(f"\n📄 Fixed code preview:")
            print("-" * 50)
            fixed_code = (sandbox_path / "bad_code.py").read_text()
            print(fixed_code[:500])
            if len(fixed_code) > 500:
                print("...")
        
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
    test_real_worktree_fixing()
