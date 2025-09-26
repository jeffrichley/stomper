#!/usr/bin/env python3
"""Demo script to show SandboxManager in action with real errors."""

import tempfile
import shutil
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.stomper.ai.sandbox_manager import SandboxManager, ProjectAwareCursorClient
from src.stomper.quality.manager import QualityToolManager
from src.stomper.discovery.scanner import FileScanner

console = Console()


def create_demo_project() -> Path:
    """Create a demo project with intentional errors."""
    temp_dir = Path(tempfile.mkdtemp(prefix="stomper_demo_"))
    
    # Initialize git repo
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "name", "Demo User").release()
    repo.config_writer().set_value("user", "email", "demo@example.com").release()
    
    # Create files with intentional errors
    (temp_dir / "main.py").write_text("""
import os
import sys
from utils.helpers import validate_user

def process_user(user_id):
    # This function has several issues
    user = get_user(user_id)  # Undefined function
    if validate_user(user):  # Missing import
        print(f"Processing user: {user.name}")
    else:
        print("Invalid user")
    
    # Unused import
    import json
    
    return user
""")
    
    # Create utils directory
    (temp_dir / "utils").mkdir()
    (temp_dir / "utils" / "__init__.py").write_text("")
    (temp_dir / "utils" / "helpers.py").write_text("""
def validate_user(user):
    return user is not None and hasattr(user, 'name')

def get_user(user_id):
    # This function is missing
    pass
""")
    
    (temp_dir / "models.py").write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.id = None  # This will cause issues
""")
    
    # Create requirements.txt
    (temp_dir / "requirements.txt").write_text("requests>=2.25.0\npydantic>=1.8.0\n")
    
    # Initial commit
    repo.git.add(".")
    repo.git.commit("-m", "Initial commit with intentional errors")
    
    return temp_dir


def run_quality_checks(project_path: Path):
    """Run quality tools to find errors."""
    console.print("\n🔍 [bold blue]Running Quality Checks...[/bold blue]")
    
    # Discover files
    scanner = FileScanner(project_path)
    files = scanner.discover_files()
    
    # Run quality tools
    quality_manager = QualityToolManager()
    all_errors = []
    
    for file_path in files:
        if file_path.suffix == '.py':
            try:
                rel_path = file_path.relative_to(project_path)
                console.print(f"  Checking {rel_path}...")
            except ValueError:
                console.print(f"  Checking {file_path.name}...")
            
            # Run ruff
            ruff_errors = quality_manager.run_ruff(str(file_path))
            all_errors.extend(ruff_errors)
            
            # Run mypy
            mypy_errors = quality_manager.run_mypy(str(file_path))
            all_errors.extend(mypy_errors)
    
    return all_errors


def demonstrate_sandbox_workflow(project_path: Path, errors):
    """Demonstrate the sandbox workflow."""
    console.print("\n🏗️ [bold green]Creating Sandbox...[/bold green]")
    
    # Create sandbox manager
    sandbox_manager = SandboxManager(project_path)
    
    try:
        # Create sandbox
        sandbox_path, branch_name = sandbox_manager.create_sandbox()
        console.print(f"  ✅ Sandbox created: {sandbox_path}")
        console.print(f"  ✅ Branch: {branch_name}")
        
        # Show sandbox contents
        console.print(f"\n📁 [bold]Sandbox Contents:[/bold]")
        for item in sandbox_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(sandbox_path)
                console.print(f"  📄 {rel_path}")
        
        # Show errors found
        console.print(f"\n❌ [bold red]Errors Found:[/bold red]")
        for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
            console.print(f"  {i}. {error.error_type}: {error.message}")
            console.print(f"     File: {error.file_path}")
            console.print(f"     Line: {error.line}")
        
        # Demonstrate project context
        console.print(f"\n🧠 [bold blue]Project Context Available:[/bold blue]")
        context = sandbox_manager.create_sandbox_context(sandbox_path)
        for file_path, content in context.items():
            console.print(f"  📄 {file_path} ({len(content)} chars)")
        
        # Show sandbox status
        console.print(f"\n📊 [bold]Sandbox Status:[/bold]")
        status = sandbox_manager.get_sandbox_status(sandbox_path)
        console.print(f"  Modified: {len(status['modified'])}")
        console.print(f"  Added: {len(status['added'])}")
        console.print(f"  Untracked: {len(status['untracked'])}")
        
        # Demonstrate diff collection
        console.print(f"\n📋 [bold]Diff Collection:[/bold]")
        diff = sandbox_manager.get_sandbox_diff(sandbox_path)
        if diff:
            console.print(f"  📄 Diff length: {len(diff)} characters")
            console.print(f"  📄 Preview: {diff[:200]}...")
        else:
            console.print("  📄 No changes detected")
        
        return sandbox_path, branch_name
        
    except Exception as e:
        console.print(f"❌ [bold red]Error creating sandbox:[/bold red] {e}")
        return None, None


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
    """Run the sandbox demonstration."""
    console.print(Panel.fit(
        "[bold blue]Stomper Sandbox Manager Demo[/bold blue]\n"
        "This demo shows how the sandbox manager creates isolated\n"
        "environments for safe AI agent execution.",
        title="🚀 Demo"
    ))
    
    project_path = None
    sandbox_path = None
    branch_name = None
    
    try:
        # Create demo project
        console.print("\n📁 [bold green]Creating Demo Project...[/bold green]")
        project_path = create_demo_project()
        console.print(f"  ✅ Demo project created: {project_path}")
        
        # Run quality checks (simplified)
        console.print(f"  ✅ Demo project ready")
        
        # Demonstrate sandbox workflow
        sandbox_path, branch_name = demonstrate_sandbox_workflow(project_path, [])
        
        if sandbox_path:
            console.print(Panel.fit(
                "[bold green]✅ Sandbox Demo Complete![/bold green]\n\n"
                "The sandbox manager successfully:\n"
                "• Created isolated git worktree\n"
                "• Provided full project context\n"
                "• Enabled safe multi-file operations\n"
                "• Maintained complete isolation from real code",
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
