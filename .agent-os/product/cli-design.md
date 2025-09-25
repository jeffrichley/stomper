# Stomper CLI Design

## CLI Interface with Typer

### Main Command Structure
```python
import typer
from typing import Optional, List
from enum import Enum

class QualityTool(str, Enum):
    RUFF = "ruff"
    MYPY = "mypy"
    DRILL_SERGEANT = "drill-sergeant"

app = typer.Typer(help="Automated code quality fixing tool")

@app.command()
def fix(
    # Quality tool flags (core tools)
    ruff: bool = typer.Option(True, "--ruff/--no-ruff", help="Enable/disable Ruff linting"),
    mypy: bool = typer.Option(True, "--mypy/--no-mypy", help="Enable/disable MyPy type checking"),
    drill_sergeant: bool = typer.Option(False, "--drill-sergeant/--no-drill-sergeant", help="Enable/disable Drill Sergeant"),
    
    # Custom tools
    extra_tools: Optional[List[str]] = typer.Option(None, "--extra-tools", help="Additional custom tools to run (comma-separated)"),
    
    # Processing options
    files: Optional[List[str]] = typer.Option(None, "--file", "-f", help="Specific files to process"),
    max_errors: Optional[int] = typer.Option(None, "--max-errors", help="Maximum errors to fix per iteration"),
    error_types: Optional[List[str]] = typer.Option(None, "--error-type", help="Specific error types to fix (e.g., E501, F401)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive error type selection"),
    
    # AI agent options
    agent: str = typer.Option("cursor-cli", "--agent", help="AI agent to use"),
    max_retries: int = typer.Option(3, "--max-retries", help="Maximum retry attempts per file"),
    
    # Execution options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fixed without making changes"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
    
    # Advanced options
    parallel: bool = typer.Option(False, "--parallel", help="Process files in parallel (experimental)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Fix code quality issues using AI agents."""
    pass
```

### Usage Examples
```bash
# Basic usage - fix all issues with default tools
stomper fix

# Only fix Ruff issues
stomper fix --no-mypy --no-drill-sergeant

# Add custom tools
stomper fix --extra-tools black,isort,bandit

# Fix specific files
stomper fix --file src/auth.py --file src/models.py

# Fix only line length issues (E501)
stomper fix --error-type E501

# Interactive error type selection
stomper fix --interactive

# Fix maximum 5 errors per iteration
stomper fix --max-errors 5

# Dry run to see what would be fixed
stomper fix --dry-run

# Use custom configuration
stomper fix --config ./stomper.toml

# Verbose output with specific agent
stomper fix --agent cursor-cli --verbose
```

## Dynamic Tool Flag Generation

### Automatic Flag Generation
```python
import typer
from typing import Dict, Any
import inspect

class DynamicToolFlags:
    """Dynamically generate --tool and --no-tool flags for custom tools."""
    
    def __init__(self, extra_tools: List[str]):
        self.extra_tools = extra_tools
        self.tool_flags = {}
    
    def generate_flags(self) -> Dict[str, Any]:
        """Generate dynamic flags for extra tools."""
        flags = {}
        
        for tool in self.extra_tools:
            # Create --tool/--no-tool flag pair
            flag_name = f"{tool}/--no-{tool}"
            flags[tool] = typer.Option(
                True, 
                f"--{flag_name}", 
                help=f"Enable/disable {tool}"
            )
        
        return flags

# Usage in CLI
def create_dynamic_cli(extra_tools: List[str] = None):
    """Create CLI with dynamic tool flags."""
    app = typer.Typer()
    
    if extra_tools:
        dynamic_flags = DynamicToolFlags(extra_tools)
        tool_flags = dynamic_flags.generate_flags()
        
        @app.command()
        def fix(**kwargs):
            """Fix command with dynamic tool flags."""
            # Process dynamic flags
            enabled_tools = []
            for tool, enabled in tool_flags.items():
                if kwargs.get(tool, True):
                    enabled_tools.append(tool)
            
            return enabled_tools
    
    return app
```

### Configuration-Based Tool Discovery
```python
def discover_available_tools(config: StomperConfig) -> List[str]:
    """Discover tools from configuration and generate flags."""
    available_tools = []
    
    # Core tools
    available_tools.extend(["ruff", "mypy", "drill-sergeant"])
    
    # Tools from configuration
    if config.tools:
        available_tools.extend(config.tools.keys())
    
    # Tools from extra_tools flag
    if config.extra_tools:
        available_tools.extend(config.extra_tools)
    
    return list(set(available_tools))  # Remove duplicates

# Example: Auto-generate flags for all discovered tools
def create_cli_with_auto_flags():
    """Create CLI that automatically generates flags for all available tools."""
    config = load_config()
    available_tools = discover_available_tools(config)
    
    # Generate flags dynamically
    flags = {}
    for tool in available_tools:
        flags[tool] = typer.Option(
            tool in ["ruff", "mypy"],  # Default enabled tools
            f"--{tool}/--no-{tool}",
            help=f"Enable/disable {tool}"
        )
    
    return flags
```

## Interactive Error Type Selection

### Error Type Discovery and Selection
```python
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def discover_error_types(files: List[str], enabled_tools: List[str]) -> Dict[str, List[str]]:
    """Discover all error types across files and tools."""
    error_types = {}
    
    for file_path in files:
        for tool in enabled_tools:
            errors = run_quality_tool(tool, file_path)
            for error in errors:
                error_code = error.get("code", "unknown")
                if error_code not in error_types:
                    error_types[error_code] = []
                error_types[error_code].append({
                    "tool": tool,
                    "file": file_path,
                    "message": error.get("message", ""),
                    "count": 1
                })
    
    # Aggregate counts
    for error_code, error_list in error_types.items():
        total_count = len(error_list)
        error_types[error_code] = {
            "count": total_count,
            "tools": list(set(error["tool"] for error in error_list)),
            "files": list(set(error["file"] for error in error_list)),
            "sample_message": error_list[0]["message"] if error_list else ""
        }
    
    return error_types

def interactive_error_selection(files: List[str], enabled_tools: List[str]) -> List[str]:
    """Interactive error type selection with rich UI."""
    console.print("\n[bold blue]Discovering error types...[/bold blue]")
    
    error_types = discover_error_types(files, enabled_tools)
    
    if not error_types:
        console.print("[green]No errors found! 🎉[/green]")
        return []
    
    # Display error types in a table
    table = Table(title="Available Error Types")
    table.add_column("Error Code", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Tools", style="yellow")
    table.add_column("Files", style="green")
    table.add_column("Sample Message", style="white")
    
    for error_code, info in sorted(error_types.items()):
        table.add_row(
            error_code,
            str(info["count"]),
            ", ".join(info["tools"]),
            str(len(info["files"])),
            info["sample_message"][:50] + "..." if len(info["sample_message"]) > 50 else info["sample_message"]
        )
    
    console.print(table)
    
    # Selection options
    console.print("\n[bold]Selection Options:[/bold]")
    console.print("1. [cyan]All[/cyan] - Fix all error types")
    console.print("2. [cyan]Interactive[/cyan] - Select specific error types")
    console.print("3. [cyan]Auto[/cyan] - Let stomper choose the best strategy")
    
    choice = Prompt.ask("Choose selection method", choices=["all", "interactive", "auto"], default="auto")
    
    if choice == "all":
        return list(error_types.keys())
    
    elif choice == "interactive":
        selected_errors = []
        
        for error_code, info in sorted(error_types.items()):
            console.print(f"\n[bold]Error: {error_code}[/bold]")
            console.print(f"Count: {info['count']} | Tools: {', '.join(info['tools'])}")
            console.print(f"Sample: {info['sample_message']}")
            
            if Confirm.ask(f"Fix {error_code} errors?", default=True):
                selected_errors.append(error_code)
        
        return selected_errors
    
    else:  # auto
        # Auto-select based on strategy
        return auto_select_error_types(error_types)

def auto_select_error_types(error_types: Dict[str, Dict]) -> List[str]:
    """Automatically select error types based on strategy."""
    # Strategy: Select most common errors first, but limit to reasonable number
    sorted_errors = sorted(
        error_types.items(), 
        key=lambda x: x[1]["count"], 
        reverse=True
    )
    
    # Select top 5 most common error types
    selected = [error_code for error_code, _ in sorted_errors[:5]]
    
    console.print(f"[bold]Auto-selected {len(selected)} error types:[/bold] {', '.join(selected)}")
    
    return selected
```

### Integration with Main CLI
```python
@app.command()
def fix(
    # ... existing parameters ...
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive error type selection"),
):
    """Fix code quality issues using AI agents."""
    
    # Determine files to process
    files = determine_files_to_process(files_param)
    
    # Determine enabled tools
    enabled_tools = determine_enabled_tools(
        ruff, mypy, drill_sergeant, extra_tools
    )
    
    # Handle error type selection
    if interactive and not error_types:
        # Interactive selection
        selected_error_types = interactive_error_selection(files, enabled_tools)
    elif not error_types:
        # Auto-selection based on strategy
        error_types = auto_select_error_types(files, enabled_tools)
    else:
        # Use provided error types
        selected_error_types = error_types
    
    # Continue with processing...
    process_files_with_error_types(files, enabled_tools, selected_error_types)
```

## Tool Execution System

### UV Integration
```python
import subprocess
import shutil
from pathlib import Path

def detect_project_manager() -> str:
    """Detect if running in UV, Poetry, or pip project."""
    if Path("pyproject.toml").exists():
        # Check for UV lock file
        if Path("uv.lock").exists():
            return "uv"
        # Check for Poetry lock file
        elif Path("poetry.lock").exists():
            return "poetry"
    return "pip"

def run_quality_tool(tool: str, args: List[str], cwd: Path = None, config: StomperConfig = None) -> subprocess.CompletedProcess:
    """Run quality tool with hybrid approach: custom config first, then auto-detection."""
    
    # Option B: Try custom configuration first
    if config and config.has_custom_command(tool):
        cmd = config.get_custom_command(tool)
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    # Option A: Fall back to direct execution with package manager detection
    project_manager = detect_project_manager()
    
    if project_manager == "uv":
        cmd = ["uv", "run", tool] + args
    elif project_manager == "poetry":
        cmd = ["poetry", "run", tool] + args
    else:
        cmd = [tool] + args
    
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
```

### Customizable Tool Commands
```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class ToolConfig(BaseModel):
    command: str
    args: List[str] = []
    working_dir: Optional[str] = None
    environment: Dict[str, str] = {}

class StomperConfig(BaseModel):
    tools: Dict[str, ToolConfig] = {
        "ruff": ToolConfig(
            command="ruff",
            args=["check", "--output-format=json", "src/"]
        ),
        "mypy": ToolConfig(
            command="mypy", 
            args=["--show-error-codes", "--json-report", ".", "src/"]
        ),
        "drill-sergeant": ToolConfig(
            command="drill-sergeant",
            args=["--json", "tests/"]
        )
    }
```

## Configuration System

### Configuration File Priority
1. `stomper.toml` (project root) - Dedicated stomper configuration
2. `pyproject.toml` → `[tool.stomper]` - Integrated with project config
3. Default configuration - Built-in defaults

### stomper.toml Example
```toml
# stomper.toml
[tool.stomper]
ai_agent = "cursor-cli"
max_retries = 3
parallel_files = 1
dry_run = false

# Tool configurations (hybrid approach)
[tool.stomper.tools.ruff]
command = "uv run ruff check --output-format=json src/"
# OR use args array:
# command = "uv run ruff"
# args = ["check", "--output-format=json", "src/"]

[tool.stomper.tools.mypy]
command = "uv run mypy --show-error-codes --json-report . src/"

[tool.stomper.tools.drill-sergeant]
command = "uv run drill-sergeant --json tests/"

# Custom tools
[tool.stomper.tools.black]
command = "uv run black --check --diff src/"

[tool.stomper.tools.isort]
command = "uv run isort --check-only --diff src/"

# Processing options
[tool.stomper.processing]
max_errors_per_iteration = 5
max_error_types_per_iteration = 2
enable_auto_fix = true

# Ignore patterns
[tool.stomper.ignores]
files = ["tests/**", "migrations/**", "*.pyc"]
errors = ["E501", "F401"]

# Git configuration
[tool.stomper.git]
branch_prefix = "stomper"
commit_style = "conventional"
auto_commit = true
```

### pyproject.toml Integration
```toml
# pyproject.toml
[tool.stomper]
ai_agent = "cursor-cli"
max_retries = 3

[tool.stomper.tools.ruff]
command = "uv run ruff"

[tool.stomper.ignores]
files = ["tests/**"]
errors = ["E501"]
```

## Granular Error Processing

### Processing Strategies
```python
class ProcessingStrategy(str, Enum):
    ONE_ERROR_TYPE = "one_error_type"      # Fix one error type at a time
    ONE_ERROR_PER_FILE = "one_error_per_file"  # Fix one error per file per iteration
    BATCH_ERRORS = "batch_errors"          # Fix multiple errors up to limit
    ALL_ERRORS = "all_errors"             # Fix all errors in file

class ProcessingConfig(BaseModel):
    strategy: ProcessingStrategy = ProcessingStrategy.BATCH_ERRORS
    max_errors_per_iteration: int = 5
    max_error_types_per_iteration: int = 2
    enable_auto_fix: bool = True
```

### Error Processing Flow
```python
def process_file_granular(file_path: Path, config: ProcessingConfig) -> ProcessingResult:
    """Process file with granular error control."""
    errors = collect_errors_for_file(file_path)
    
    if config.strategy == ProcessingStrategy.ONE_ERROR_TYPE:
        # Fix one error type at a time
        for error_type in errors.grouped_by_type():
            fix_errors_of_type(file_path, error_type)
            if not verify_fixes(file_path, error_type):
                break
    
    elif config.strategy == ProcessingStrategy.ONE_ERROR_PER_FILE:
        # Fix one error per iteration
        for error in errors:
            fix_single_error(file_path, error)
            if not verify_single_fix(file_path, error):
                break
    
    elif config.strategy == ProcessingStrategy.BATCH_ERRORS:
        # Fix up to max_errors_per_iteration
        batch = errors[:config.max_errors_per_iteration]
        fix_error_batch(file_path, batch)
    
    else:  # ALL_ERRORS
        fix_all_errors(file_path, errors)
    
    return ProcessingResult(success=True)
```
