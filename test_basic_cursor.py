 #!/usr/bin/env python3
"""Test cursor-agent with basic flags and simple question."""

import subprocess
import tempfile
from pathlib import Path

def test_basic_cursor():
    """Test cursor-agent with basic flags and simple math question."""
    
    # Create a temporary directory for the test
    temp_dir = Path(tempfile.mkdtemp(prefix="cursor_test_"))
    
    print(f"Created test directory: {temp_dir}")
    
    # Test basic cursor-agent command with simple question
    cmd = [
        "cursor-agent",
        "--print",
        "-f",
        "--output-format", "text",
        "agent",
        "What is 2+2?"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {temp_dir}")
    
    try:
        # Use Popen for better subprocess handling
        process = subprocess.Popen(
            cmd,
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Use communicate with timeout
        try:
            stdout, stderr = process.communicate(timeout=30)
            print(f"\nReturn code: {process.returncode}")
            print(f"Stdout:\n{stdout}")
            print(f"Stderr:\n{stderr}")
            
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print("Command timed out after 30 seconds!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up: {temp_dir}")

if __name__ == "__main__":
    test_basic_cursor()
