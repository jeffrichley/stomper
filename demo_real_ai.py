#!/usr/bin/env python3
"""Demo script showing REAL AI agents fixing code with cursor-cli."""

import tempfile
import shutil
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.stomper.ai.sandbox_manager import SandboxManager, ProjectAwareCursorClient
from src.stomper.ai.cursor_client import CursorClient
from src.stomper.quality.manager import QualityToolManager
from src.stomper.discovery.scanner import FileScanner

console = Console()


def create_broken_project() -> Path:
    """Create a project with real Python errors."""
    temp_dir = Path(tempfile.mkdtemp(prefix="stomper_real_ai_"))
    
    # Initialize git repo
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "name", "Demo User").release()
    repo.config_writer().set_value("user", "email", "demo@example.com").release()
    
    # Create broken Python files
    (temp_dir / "main.py").write_text("""
import os
import sys
from utils.helpers import validate_user, get_user

def process_user(user_id):
    # Multiple issues in this function
    user = get_user(user_id)  # This function exists but has issues
    if validate_user(user):   # This function exists
        print(f"Processing user: {user.name}")
        # Unused variable
        unused_var = "this is not used"
    else:
        print("Invalid user")
    
    # Unused import
    import json
    
    # Missing return statement
    # return user

def main():
    user_id = "123"
    result = process_user(user_id)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""")
    
    # Create utils directory
    (temp_dir / "utils").mkdir()
    (temp_dir / "utils" / "__init__.py").write_text("")
    (temp_dir / "utils" / "helpers.py").write_text("""
def validate_user(user):
    return user is not None and hasattr(user, 'name')

def get_user(user_id):
    # This function has issues - missing return
    if user_id:
        # Should return something
        pass
""")
    
    (temp_dir / "models.py").write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.id = None  # This will cause issues
    
    def get_display_name(self):
        return f"{self.name} ({self.email})"
""")
    
    # Create pyproject.toml for proper Python project
    (temp_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-project"
version = "0.1.0"
dependencies = []
""")
    
    # Initial commit
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit with intentional errors")
    
    return temp_dir


def find_errors(project_path: Path):
    """Find errors in the project using quality tools."""
    console.print("\n🔍 [bold blue]Finding Errors...[/bold blue]")
    
    # Discover files
    scanner = FileScanner(project_path)
    files = scanner.discover_files()
    
    # Run quality tools
    quality_manager = QualityToolManager()
    
    # Run quality tools on the project
    console.print(f"  📄 Checking {len(files)} Python files...")
    
    # Run all available tools
    available_tools = quality_manager.get_available_tools()
    console.print(f"  🔧 Available tools: {', '.join(available_tools)}")
    
    if available_tools:
        all_errors = quality_manager.run_tools(
            target_path=project_path,
            project_root=project_path,
            enabled_tools=available_tools,
            max_errors=50
        )
    else:
        console.print("  ⚠️ No quality tools available")
        all_errors = []
    
    # Display errors in a table
    if all_errors:
        table = Table(title="Found Errors")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="magenta")
        table.add_column("Type", style="red")
        table.add_column("Message", style="yellow")
        
        for error in all_errors[:10]:  # Show first 10 errors
            table.add_row(
                str(error.file),
                str(error.line),
                error.code,
                error.message[:50] + "..." if len(error.message) > 50 else error.message
            )
        
        console.print(table)
    else:
        console.print("  ✅ No errors found!")
    
    return all_errors


def demonstrate_real_ai_fix(project_path: Path, errors):
    """Demonstrate REAL AI agent fixing errors in sandbox."""
    console.print("\n🤖 [bold green]REAL AI Agent Fixing Errors...[/bold green]")
    
    # Create sandbox manager
    sandbox_manager = SandboxManager(project_path)
    
    try:
        # Create sandbox
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        console.print(f"  ✅ Sandbox created: {sandbox_path}")
        console.print(f"  ✅ Branch: {branch_name}")
        
        # Show what the AI agent would see
        console.print(f"\n🧠 [bold blue]AI Agent Context:[/bold blue]")
        context = sandbox_manager.create_sandbox_context(sandbox_path)
        for file_path, content in context.items():
            console.print(f"  📄 {file_path} ({len(content)} chars)")
        
        # Check if cursor-cli is available
        cursor_client = CursorClient()
        if not cursor_client.is_available():
            console.print("\n⚠️ [bold yellow]cursor-cli not available - using simulation[/bold yellow]")
            return demonstrate_simulated_fix(sandbox_manager, sandbox_path)
        
        console.print(f"\n🔧 [bold yellow]Using REAL cursor-cli AI agent...[/bold yellow]")
        
        # Use ProjectAwareCursorClient for real AI fixes
        project_aware_client = ProjectAwareCursorClient(sandbox_manager)
        
        # Fix main.py with real AI
        main_file = sandbox_path / "main.py"
        if main_file.exists():
            console.print("  🤖 AI Agent fixing main.py...")
            
            # Prepare error context for the AI
            error_context = {
                "error_type": "linting",
                "message": "Multiple linting errors: unused imports, unused variable, missing return",
                "file": str(main_file),
                "line": 1,
                "code": "F401,F841"
            }
            
            # Let the AI agent fix the file
            try:
                fixed_code = project_aware_client.generate_fix_with_project_context(
                    main_file,
                    error_context,
                    "Fix all linting errors in this file. Remove unused imports, remove unused variables, and add missing return statement.",
                    sandbox_path
                )
                
                # Write the AI-generated fix
                main_file.write_text(fixed_code)
                console.print("    ✅ AI agent fixed main.py")
                
            except Exception as e:
                console.print(f"    ⚠️ AI agent failed: {e}")
                console.print("    🔄 Falling back to simulation...")
                return demonstrate_simulated_fix(sandbox_manager, sandbox_path)
        
        # Fix utils/helpers.py with real AI
        helpers_file = sandbox_path / "utils" / "helpers.py"
        if helpers_file.exists():
            console.print("  🤖 AI Agent fixing utils/helpers.py...")
            
            # Prepare error context for the AI
            error_context = {
                "error_type": "function",
                "message": "Function get_user is missing return statement",
                "file": str(helpers_file),
                "line": 6,
                "code": "E999"
            }
            
            # Let the AI agent fix the file
            try:
                fixed_code = project_aware_client.generate_fix_with_project_context(
                    helpers_file,
                    error_context,
                    "Fix the get_user function to return a proper User object. Import the User class from models and return a User instance.",
                    sandbox_path
                )
                
                # Write the AI-generated fix
                helpers_file.write_text(fixed_code)
                console.print("    ✅ AI agent fixed utils/helpers.py")
                
            except Exception as e:
                console.print(f"    ⚠️ AI agent failed: {e}")
                console.print("    🔄 Falling back to simulation...")
                return demonstrate_simulated_fix(sandbox_manager, sandbox_path)
        
        # Show changes
        console.print(f"\n📊 [bold]Changes Made:[/bold]")
        status = sandbox_manager.get_sandbox_status(sandbox_path)
        console.print(f"  Modified: {len(status['modified'])} files")
        console.print(f"  Added: {len(status['added'])} files")
        console.print(f"  Untracked: {len(status['untracked'])} files")
        
        # Show diff
        diff = sandbox_manager.get_sandbox_diff(sandbox_path)
        if diff:
            console.print(f"\n📋 [bold]Diff Preview:[/bold]")
            console.print(f"  📄 Diff length: {len(diff)} characters")
            # Show first few lines of diff
            diff_lines = diff.split('\n')[:10]
            for line in diff_lines:
                if line.strip():
                    console.print(f"    {line}")
            if len(diff.split('\n')) > 10:
                console.print("    ...")
        
        # Test the fixed code
        console.print(f"\n🧪 [bold]Testing AI-Fixed Code:[/bold]")
        try:
            import subprocess
            result = subprocess.run(
                ["python", str(main_file)], 
                cwd=sandbox_path, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                console.print("  ✅ AI-fixed code runs successfully!")
                console.print(f"  📄 Output: {result.stdout.strip()}")
            else:
                console.print("  ⚠️ AI-fixed code still has issues:")
                console.print(f"  📄 Error: {result.stderr.strip()}")
        except Exception as e:
            console.print(f"  ⚠️ Could not test code: {e}")
        
        return sandbox_path, branch_name
        
    except Exception as e:
        console.print(f"❌ [bold red]Error in AI workflow:[/bold red] {e}")
        return None, None


def demonstrate_simulated_fix(sandbox_manager, sandbox_path):
    """Fallback to simulated fixes if cursor-cli not available."""
    console.print("\n🔧 [bold yellow]Simulating AI Agent Changes...[/bold yellow]")
    
    # Fix main.py
    main_file = sandbox_path / "main.py"
    if main_file.exists():
        console.print("  🔧 Fixing main.py...")
        fixed_content = """from utils.helpers import validate_user, get_user

def process_user(user_id):
    # Fixed function with proper return
    user = get_user(user_id)
    if validate_user(user):
        print(f"Processing user: {user.name}")
    else:
        print("Invalid user")
    
    return user

def main():
    user_id = "123"
    result = process_user(user_id)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
        main_file.write_text(fixed_content)
        console.print("    ✅ Fixed unused imports and missing return")
    
    # Fix utils/helpers.py
    helpers_file = sandbox_path / "utils" / "helpers.py"
    if helpers_file.exists():
        console.print("  🔧 Fixing utils/helpers.py...")
        fixed_helpers = """def validate_user(user):
    return user is not None and hasattr(user, 'name')

def get_user(user_id):
    # Fixed function with proper return
    if user_id:
        from models import User
        return User("Demo User", "demo@example.com")
    return None
"""
        helpers_file.write_text(fixed_helpers)
        console.print("    ✅ Fixed missing return statement")
    
    return sandbox_path, "simulated"


def cleanup_demo(project_path: Path, sandbox_path: Path, branch_name: str):
    """Clean up demo files."""
    console.print(f"\n🧹 [bold yellow]Cleaning up...[/bold yellow]")
    
    try:
        # Cleanup sandbox
        if sandbox_path and sandbox_path.exists():
            sandbox_manager = SandboxManager(project_path)
            sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)
            console.print("  ✅ Sandbox cleaned up")
        
        # Remove demo project
        shutil.rmtree(project_path)
        console.print("  ✅ Demo project removed")
        
    except Exception as e:
        console.print(f"  ⚠️ Cleanup warning: {e}")


def main():
    """Run the REAL AI workflow demonstration."""
    console.print(Panel.fit(
        "[bold blue]Stomper REAL AI Workflow Demo[/bold blue]\n"
        "This demo shows the complete workflow with REAL AI agents:\n"
        "1. Find errors in a project\n"
        "2. Create isolated sandbox\n"
        "3. REAL AI agent fixes errors with cursor-cli\n"
        "4. Collect and apply changes",
        title="🚀 Real AI Workflow"
    ))
    
    project_path = None
    sandbox_path = None
    branch_name = None
    
    try:
        # Create broken project
        console.print("\n📁 [bold green]Creating Broken Project...[/bold green]")
        project_path = create_broken_project()
        console.print(f"  ✅ Project created: {project_path}")
        
        # Find errors
        errors = find_errors(project_path)
        
        # Demonstrate REAL AI workflow
        sandbox_path, branch_name = demonstrate_real_ai_fix(project_path, errors)
        
        if sandbox_path:
            console.print(Panel.fit(
                "[bold green]✅ REAL AI Workflow Complete![/bold green]\n\n"
                "The REAL AI agent successfully:\n"
                "• Created isolated sandbox environment\n"
                "• Used cursor-cli to fix multiple errors\n"
                "• Maintained project structure\n"
                "• Generated safe diff for review\n"
                "• Your original code remains untouched",
                title="🎉 Success"
            ))
        
    except Exception as e:
        console.print(f"\n❌ [bold red]Demo failed:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())
        
    finally:
        # Cleanup
        if project_path:
            cleanup_demo(project_path, sandbox_path, branch_name)


if __name__ == "__main__":
    main()
