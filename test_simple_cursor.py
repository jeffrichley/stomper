#!/usr/bin/env python3
"""Test cursor-agent with simple prompt."""

import tempfile
import subprocess
from pathlib import Path
from src.stomper.ai.sandbox_manager import SandboxManager

def test_simple_cursor():
    """Test cursor-agent with simple prompt."""
    # Create a simple project
    temp_dir = Path(tempfile.mkdtemp(prefix="test_simple_"))
    
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
    print(f"Test file content: {(temp_dir / 'test.py').read_text()}")
    
    # Create sandbox
    sandbox_manager = SandboxManager(temp_dir)
    sandbox_path, branch_name = sandbox_manager.create_sandbox()
    
    print(f"Created sandbox: {sandbox_path}")
    print(f"Sandbox files: {list(sandbox_path.glob('*.py'))}")
    
    # Test simple cursor-agent command
    simple_prompt = "Add a comment"
    target_file = sandbox_path / "test.py"
    
    cmd = [
        "cursor-agent",
        "--print",
        "-f",
        "--output-format", "text",
        "agent",
        simple_prompt,
        str(target_file)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {sandbox_path}")
    print(f"Target file exists: {target_file.exists()}")
    print(f"Target file content: {target_file.read_text()}")
    
    try:
        # Use Popen for better subprocess handling
        process = subprocess.Popen(
            cmd,
            cwd=sandbox_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Use communicate with timeout
        try:
            stdout, stderr = process.communicate(timeout=60)
            print(f"Return code: {process.returncode}")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
            
            # Check if file was modified
            if target_file.exists():
                print(f"Modified file content: {target_file.read_text()}")
            else:
                print("File was deleted!")
                
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print("Command timed out after 60 seconds!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
        import shutil
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_simple_cursor()
