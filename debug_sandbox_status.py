#!/usr/bin/env python3
"""Debug sandbox status functionality."""

import tempfile
from pathlib import Path
from src.stomper.ai.sandbox_manager import SandboxManager
from git import Repo

def debug_sandbox_status():
    """Debug the sandbox status functionality."""
    print("=" * 60)
    print("DEBUGGING SANDBOX STATUS")
    print("=" * 60)
    
    # Create test project
    temp_dir = Path(tempfile.mkdtemp(prefix="debug_sandbox_"))
    print(f"Created test project: {temp_dir}")
    
    try:
        # Initialize git repo
        repo = Repo.init(temp_dir)
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()
        
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello world')")
        
        # Add and commit
        repo.git.add(".")
        repo.git.commit("-m", "Initial commit")
        print("✅ Created initial commit")
        
        # Create sandbox
        sandbox_manager = SandboxManager(temp_dir)
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        print(f"✅ Created sandbox: {sandbox_path}")
        
        # Check initial status
        print(f"\n🔍 Initial sandbox status:")
        initial_status = sandbox_manager.get_sandbox_status(sandbox_path)
        print(f"  Modified: {initial_status['modified']}")
        print(f"  Added: {initial_status['added']}")
        print(f"  Deleted: {initial_status['deleted']}")
        print(f"  Untracked: {initial_status['untracked']}")
        
        # Make a change to the file
        print(f"\n📝 Making a change to test.py...")
        test_file_sandbox = sandbox_path / "test.py"
        original_content = test_file_sandbox.read_text()
        test_file_sandbox.write_text("print('hello world')\nprint('modified!')")
        print(f"✅ Modified file content")
        
        # Check status after modification
        print(f"\n🔍 Status after modification:")
        modified_status = sandbox_manager.get_sandbox_status(sandbox_path)
        print(f"  Modified: {modified_status['modified']}")
        print(f"  Added: {modified_status['added']}")
        print(f"  Deleted: {modified_status['deleted']}")
        print(f"  Untracked: {modified_status['untracked']}")
        
        # Let's also check git status manually
        print(f"\n🔍 Manual git status check:")
        sandbox_repo = Repo(sandbox_path)
        status_output = sandbox_repo.git.status("--porcelain")
        print(f"Git status output: '{status_output}'")
        
        # Parse the status output manually
        print(f"\n🔍 Parsing status output:")
        for line in status_output.split('\n'):
            if line.strip():
                print(f"  Line: '{line}'")
                status_code = line[:2]
                filename = line[3:]
                print(f"    Status code: '{status_code}'")
                print(f"    Filename: '{filename}'")
                
                if status_code.startswith('M'):
                    print(f"    -> MODIFIED")
                elif status_code.startswith('A'):
                    print(f"    -> ADDED")
                elif status_code.startswith('D'):
                    print(f"    -> DELETED")
                elif status_code.startswith('??'):
                    print(f"    -> UNTRACKED")
                else:
                    print(f"    -> UNKNOWN STATUS CODE")
        
        # Check if the file actually changed
        print(f"\n🔍 File content check:")
        print(f"  Original: {repr(original_content)}")
        print(f"  Current:  {repr(test_file_sandbox.read_text())}")
        print(f"  Changed: {original_content != test_file_sandbox.read_text()}")
        
        # Try to get diff
        print(f"\n🔍 Getting diff:")
        diff = sandbox_manager.get_sandbox_diff(sandbox_path)
        print(f"  Diff length: {len(diff)} characters")
        if diff:
            print(f"  Diff preview: {diff[:200]}...")
        else:
            print(f"  No diff found")
        
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
    debug_sandbox_status()
