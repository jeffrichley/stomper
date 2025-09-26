#!/usr/bin/env python3
"""Comprehensive test of all sandbox status functionality."""

import tempfile
from pathlib import Path
from src.stomper.ai.sandbox_manager import SandboxManager
from git import Repo

def test_all_sandbox_status_scenarios():
    """Test all sandbox status scenarios: modified, added, deleted, untracked."""
    print("=" * 60)
    print("COMPREHENSIVE SANDBOX STATUS TEST")
    print("=" * 60)
    
    # Create test project
    temp_dir = Path(tempfile.mkdtemp(prefix="test_sandbox_status_"))
    print(f"Created test project: {temp_dir}")
    
    try:
        # Initialize git repo
        repo = Repo.init(temp_dir)
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()
        
        # Create initial files
        (temp_dir / "existing.py").write_text("print('existing file')")
        (temp_dir / "to_delete.py").write_text("print('will be deleted')")
        
        # Add and commit initial files
        repo.git.add(".")
        repo.git.commit("-m", "Initial commit")
        print("✅ Created initial commit with existing files")
        
        # Create sandbox
        sandbox_manager = SandboxManager(temp_dir)
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        print(f"✅ Created sandbox: {sandbox_path}")
        
        # Check initial status (should be clean)
        print(f"\n🔍 Initial sandbox status (should be clean):")
        initial_status = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(initial_status)
        
        # Test 1: MODIFIED files
        print(f"\n📝 Test 1: MODIFYING existing file...")
        existing_file = sandbox_path / "existing.py"
        existing_file.write_text("print('existing file - MODIFIED')")
        print(f"✅ Modified existing.py")
        
        status_1 = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(status_1, "After modification")
        
        # Test 2: ADDED files (new files)
        print(f"\n📄 Test 2: ADDING new files...")
        new_file_1 = sandbox_path / "new_file.py"
        new_file_1.write_text("print('new file 1')")
        
        new_file_2 = sandbox_path / "another_new.py"
        new_file_2.write_text("print('new file 2')")
        
        # Add one file to git (staged)
        repo_sandbox = Repo(sandbox_path)
        repo_sandbox.git.add("new_file.py")
        print(f"✅ Created new_file.py and another_new.py")
        print(f"✅ Added new_file.py to git (staged)")
        
        status_2 = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(status_2, "After adding files")
        
        # Test 3: DELETED files
        print(f"\n🗑️ Test 3: DELETING file...")
        to_delete_file = sandbox_path / "to_delete.py"
        to_delete_file.unlink()
        print(f"✅ Deleted to_delete.py")
        
        status_3 = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(status_3, "After deleting file")
        
        # Test 4: UNTRACKED files (new files not added to git)
        print(f"\n📁 Test 4: UNTRACKED files...")
        untracked_file = sandbox_path / "untracked.py"
        untracked_file.write_text("print('untracked file')")
        
        untracked_dir = sandbox_path / "untracked_dir"
        untracked_dir.mkdir()
        (untracked_dir / "nested.py").write_text("print('nested untracked')")
        print(f"✅ Created untracked.py and untracked_dir/nested.py")
        
        status_4 = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(status_4, "After creating untracked files")
        
        # Test 5: Mixed scenario (all types)
        print(f"\n🔄 Test 5: MIXED scenario - all types of changes...")
        
        # Modify the untracked file
        untracked_file.write_text("print('untracked file - MODIFIED')")
        
        # Create another new file and add it
        mixed_new = sandbox_path / "mixed_new.py"
        mixed_new.write_text("print('mixed new file')")
        repo_sandbox.git.add("mixed_new.py")
        
        # Create another untracked file
        another_untracked = sandbox_path / "another_untracked.py"
        another_untracked.write_text("print('another untracked')")
        
        print(f"✅ Created mixed scenario with all change types")
        
        status_5 = sandbox_manager.get_sandbox_status(sandbox_path)
        print_status(status_5, "Mixed scenario (all change types)")
        
        # Test 6: Show git status manually for comparison
        print(f"\n🔍 Manual git status for comparison:")
        git_status = repo_sandbox.git.status("--porcelain")
        print(f"Git status output:")
        for line in git_status.split('\n'):
            if line.strip():
                print(f"  '{line}'")
        
        # Test 7: Show diff
        print(f"\n📋 Getting diff...")
        diff = sandbox_manager.get_sandbox_diff(sandbox_path)
        print(f"Diff length: {len(diff)} characters")
        if diff:
            print(f"Diff preview (first 300 chars):")
            print("-" * 50)
            print(diff[:300])
            if len(diff) > 300:
                print("...")
        else:
            print("No diff found")
        
        # Test 8: Show file tree
        print(f"\n📁 Sandbox file tree:")
        show_file_tree(sandbox_path)
        
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


def print_status(status, label="Status"):
    """Print sandbox status in a nice format."""
    print(f"  {label}:")
    print(f"    Modified: {status['modified']}")
    print(f"    Added: {status['added']}")
    print(f"    Deleted: {status['deleted']}")
    print(f"    Untracked: {status['untracked']}")
    print(f"    Total changes: {len(status['modified']) + len(status['added']) + len(status['deleted']) + len(status['untracked'])}")


def show_file_tree(path, prefix="", max_depth=3, current_depth=0):
    """Show file tree structure."""
    if current_depth >= max_depth:
        print(f"{prefix}... (max depth reached)")
        return
    
    try:
        items = sorted(path.iterdir())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir() and current_depth < max_depth - 1:
                next_prefix = prefix + ("    " if is_last else "│   ")
                show_file_tree(item, next_prefix, max_depth, current_depth + 1)
    except PermissionError:
        print(f"{prefix}[Permission denied]")


if __name__ == "__main__":
    test_all_sandbox_status_scenarios()
