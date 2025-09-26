#!/usr/bin/env python3
"""Test cursor-agent with simple prompt."""

import tempfile
import subprocess
import json
import select
import time
from pathlib import Path
from typing import Any, Dict, List
from src.stomper.ai.sandbox_manager import SandboxManager
from src.stomper.ai.cursor_client import CursorClient
from dotenv import load_dotenv
import os

load_dotenv()

# Print the CURSOR_API_KEY to verify it's loaded
print(f"CURSOR_API_KEY: {os.getenv('CURSOR_API_KEY', 'NOT SET')}")


def run_cursor_agent(cmd: List[str], cwd: str, timeout: int = 30) -> Dict[str, Any]:
    """Run cursor-agent headless, streaming and parsing output.

    Args:
        cmd: The command to execute.
        cwd: Working directory.
        timeout: Max runtime in seconds.

    Returns:
        A dict with stdout, stderr, parsed events, and final result.
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    events: List[Dict[str, Any]] = []
    result: Dict[str, Any] | None = None

    start = time.monotonic()
    try:
        while True:
            # Stop if timeout exceeded
            if time.monotonic() - start > timeout:
                raise subprocess.TimeoutExpired(cmd, timeout)

            # Process finished?
            if proc.poll() is not None:
                break

            ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.1)

            if proc.stdout in ready:
                line = proc.stdout.readline()
                if line:
                    stdout_lines.append(line)
                    print(f"[STDOUT] {line.rstrip()}")
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                        print(f"[JSON] {event}")
                        if event.get("type") == "result":
                            result = event
                            print(f"✅ Process completed successfully!")
                            print(f"Duration: {event.get('duration_ms', 0)}ms")
                            print(f"Result: {event.get('result', 'No result')}")
                            break  # Logical completion
                    except json.JSONDecodeError:
                        pass  # Keep raw text too

            if proc.stderr in ready:
                line = proc.stderr.readline()
                if line:
                    stderr_lines.append(line)
                    print(f"[STDERR] {line.rstrip()}")

        # Clean shutdown
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

    finally:
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()

    return {
        "stdout": stdout_lines,
        "stderr": stderr_lines,
        "events": events,
        "result": result,
        "returncode": proc.returncode,
    }


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
    # simple_prompt = "\"Add a comment. Do not ask any questions. Once you are finished, print 'Done stomping!' and then exit.\""
    simple_prompt = "\"Add a comment. Once you are finished, print 'Done stomping!' and then exit.\""
    target_file = sandbox_path / "test.py"

    cmd = [
        "cursor-agent",
        "-p",        # Print output to stdout
        "--force",   # Force execution
        # "--output-format", "text", # Use text output format for non-interactive use
        simple_prompt
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {sandbox_path}")
    print(f"Target file exists: {target_file.exists()}")
    print(f"Target file content: {target_file.read_text()}")
    
    print("=" * 50)
    print("STREAMING OUTPUT FROM CURSOR-AGENT:")
    print("=" * 50)
    
    try:
        # Use our Google-level subprocess runner
        result = run_cursor_agent(cmd, str(sandbox_path), timeout=30)
        
        print("=" * 50)
        print(f"Process completed with return code: {result['returncode']}")
        print(f"Total events captured: {len(result['events'])}")
        print("=" * 50)
        
        # Check if file was modified
        if target_file.exists():
            print(f"Modified file content: {target_file.read_text()}")
        else:
            print("File was deleted!")
            
        # Show structured result
        if result['result']:
            print(f"\n🎯 Final Result:")
            print(f"  Duration: {result['result'].get('duration_ms', 0)}ms")
            print(f"  Success: {not result['result'].get('is_error', True)}")
            print(f"  Content: {result['result'].get('result', 'No result')}")
            
    except subprocess.TimeoutExpired as e:
        print(f"Command timed out after 30 seconds! {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
        import shutil
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_simple_cursor()
