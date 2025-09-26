#!/usr/bin/env python3
"""Simple test to verify cursor-agent works."""

import subprocess
import tempfile
from pathlib import Path

def test_cursor_agent():
    """Test cursor-agent with a simple example."""
    # Create a simple test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("print('hello world')")
        test_file = Path(f.name)
    
    print(f"Created test file: {test_file}")
    print(f"Content: {test_file.read_text()}")
    
    # Test cursor-agent command
    cmd = [
        "cursor-agent",
        "-p",
        "--force", 
        "Add a comment to this code"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {test_file.parent}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=test_file.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if test_file.exists():
            print(f"Modified file content: {test_file.read_text()}")
        else:
            print("File was deleted!")
            
    except subprocess.TimeoutExpired:
        print("Command timed out!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    test_cursor_agent()
