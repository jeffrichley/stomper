#!/usr/bin/env python3
"""Test the integrated Google-level subprocess handling."""

import tempfile
from pathlib import Path
from src.stomper.ai.cursor_client import CursorClient
from src.stomper.ai.sandbox_manager import SandboxManager
from dotenv import load_dotenv
import os

load_dotenv()

# Print the CURSOR_API_KEY to verify it's loaded
print(f"CURSOR_API_KEY: {os.getenv('CURSOR_API_KEY', 'NOT SET')}")


def test_cursor_client_integration():
    """Test the enhanced CursorClient with streaming."""
    print("=" * 60)
    print("TESTING ENHANCED CURSOR CLIENT")
    print("=" * 60)
    
    # Create a simple project
    temp_dir = Path(tempfile.mkdtemp(prefix="test_integration_"))
    
    # Initialize git repo
    from git import Repo
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Create a simple Python file
    test_file = temp_dir / "test.py"
    test_file.write_text("print('hello world')")
    
    # Initial commit
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit")
    
    print(f"Created test project: {temp_dir}")
    print(f"Test file content: {test_file.read_text()}")
    
    # Test the enhanced cursor client (now requires sandbox_manager)
    sandbox_manager = SandboxManager(temp_dir)
    cursor_client = CursorClient(sandbox_manager)
    
    # Test basic availability
    print(f"Cursor client available: {cursor_client.is_available()}")
    
    # Create sandbox for testing
    sandbox_path, branch_name = sandbox_manager.create_sandbox()
    
    print(f"Created sandbox: {sandbox_path}")
    
    # Test the new simplified approach
    try:
        result = cursor_client.generate_fix(
            "Add a comment to this Python file. Once finished, print 'Done!' and exit.",
            sandbox_path
        )
        
        print("=" * 50)
        print(f"✅ Fix completed successfully!")
        print(f"Execution result: {result['execution_result']['returncode']}")
        print(f"Sandbox status: {result['sandbox_status']}")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup sandbox
        sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up: {temp_dir}")


def test_sandbox_manager_integration():
    """Test the enhanced SandboxManager with streaming."""
    print("\n" + "=" * 60)
    print("TESTING ENHANCED SANDBOX MANAGER")
    print("=" * 60)
    
    # Create a simple project
    temp_dir = Path(tempfile.mkdtemp(prefix="test_sandbox_"))
    
    # Initialize git repo
    from git import Repo
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Create a simple Python file
    (temp_dir / "test.py").write_text("print('hello world')")
    
    # Initial commit
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit")
    
    print(f"Created test project: {temp_dir}")
    
    # Create sandbox
    sandbox_manager = SandboxManager(temp_dir)
    sandbox_path, branch_name = sandbox_manager.create_sandbox()
    
    print(f"Created sandbox: {sandbox_path}")
    
    # Test the enhanced sandbox manager
    target_file = sandbox_path / "test.py"
    error_context = {
        "error_type": "syntax",
        "message": "Missing comment",
        "file": "test.py",
        "line": 1
    }
    prompt = "Add a helpful comment to this code"
    
    try:
        # Create cursor client with sandbox manager
        cursor_client = CursorClient(sandbox_manager)
        
        result = cursor_client.generate_fix(
            prompt,
            sandbox_path
        )
        
        print(f"✅ Sandbox manager completed successfully!")
        print(f"Execution result: {result['execution_result']['returncode']}")
        print(f"Sandbox status: {result['sandbox_status']}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up: {temp_dir}")


if __name__ == "__main__":
    test_cursor_client_integration()
    test_sandbox_manager_integration()
