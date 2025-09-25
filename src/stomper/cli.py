"""Main CLI entry point for Stomper."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from rich import box
import typer

from stomper.config.loader import ConfigLoader
from stomper.config.models import ConfigOverride
from stomper.config.validator import ConfigValidator
from stomper.discovery import FileScanner
from stomper.quality.manager import QualityToolManager

# Create the main Typer app
app = typer.Typer(
    name="stomper",
    help="Automated code quality fixing tool",
    add_completion=False,
)

# Create console for rich output
console = Console()


def print_header() -> None:
    """Print a beautiful header for Stomper."""
    header_text = Text("Stomper", style="bold blue")
    subtitle = Text("Automated Code Quality Fixing", style="italic dim")
    
    header_panel = Panel(
        Align.center(Text.assemble(header_text, "\n", subtitle)),
        box=box.DOUBLE,
        border_style="blue",
        padding=(1, 2)
    )
    console.print(header_panel)
    console.print()


def print_config_summary(config: dict, enabled_tools: list, dry_run: bool) -> None:
    """Print a beautiful configuration summary."""
    # Create a table for configuration
    table = Table(title="🔧 Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    # Tool status
    tool_status = "✅ " + ", ".join(enabled_tools) if enabled_tools else "❌ None"
    table.add_row("Enabled Tools", tool_status)
    
    # Dry run status
    dry_run_status = "🔍 Yes" if dry_run else "⚡ No"
    table.add_row("Dry Run", dry_run_status)
    
    # AI Agent
    table.add_row("AI Agent", config.get("ai_agent", "cursor-cli"))
    
    # Max retries
    table.add_row("Max Retries", str(config.get("max_retries", 3)))
    
    # Parallel files
    table.add_row("Parallel Files", str(config.get("parallel_files", 1)))
    
    console.print(table)
    console.print()


def print_file_discovery_summary(discovered_files: list, stats: dict, target_info: str) -> None:
    """Print a beautiful file discovery summary."""
    # Create columns for file info
    file_info = Table(box=box.ROUNDED)
    file_info.add_column("📁 File Discovery", style="green", no_wrap=True)
    file_info.add_column("Value", style="white")
    
    file_info.add_row("Target", target_info)
    file_info.add_row("Files Found", f"{len(discovered_files):,}")
    file_info.add_row("Total Size", f"{stats['total_size']:,} bytes")
    file_info.add_row("Directories", str(len(stats['directories'])))
    
    console.print(file_info)
    console.print()


def print_quality_results(all_errors: list, filtered_errors: list, tool_summary: dict, dry_run: bool) -> None:
    """Print beautiful quality assessment results."""
    if not filtered_errors:
        # No issues found
        success_panel = Panel(
            Align.center(Text("🎉 No matching issues found!", style="bold green")),
            box=box.ROUNDED,
            border_style="green",
            padding=(1, 2)
        )
        console.print(success_panel)
        return
    
    # Create results table
    results_table = Table(title="🔍 Quality Assessment Results", box=box.ROUNDED)
    results_table.add_column("Tool", style="cyan", no_wrap=True)
    results_table.add_column("Issues", style="red", justify="right")
    results_table.add_column("Status", style="yellow")
    
    for tool, count in tool_summary.items():
        status = "🔍 Dry Run" if dry_run else "⚡ Ready to Fix"
        results_table.add_row(tool, str(count), status)
    
    console.print(results_table)
    
    # Summary panel
    total_issues = len(all_errors)
    filtered_count = len(filtered_errors)
    
    if total_issues != filtered_count:
        summary_text = f"Found {filtered_count:,} issues to fix ({total_issues:,} total, {filtered_count:,} after filtering)"
    else:
        summary_text = f"Found {filtered_count:,} issues to fix"
    
    summary_panel = Panel(
        summary_text,
        title="📊 Summary",
        box=box.ROUNDED,
        border_style="red" if filtered_errors else "green"
    )
    console.print(summary_panel)
    
    if dry_run:
        console.print(Panel("🔍 Dry run complete - no changes made", box=box.ROUNDED, border_style="yellow"))
    else:
        console.print(Panel("⚡ Quality tool integration complete!\n🔧 Next: AI agent integration for automated fixing", box=box.ROUNDED, border_style="blue"))


def validate_file_selection(
    file: Path | None,
    files: str | None,
    directory: Path | None,
    pattern: str | None,
    git_changed: bool,
    git_staged: bool,
    git_diff: str | None,
) -> None:
    """Validate that only one file selection method is used."""
    selection_methods = [
        file is not None,
        files is not None,
        directory is not None,
        pattern is not None,
        git_changed,
        git_staged,
        git_diff is not None,
    ]

    if sum(selection_methods) > 1:
        console.print("[red]Error: Only one file selection method can be used at a time[/red]")
        console.print("[yellow]Use one of: --file, --files, --directory, --pattern, --git-changed, --git-staged, or --git-diff[/yellow]")
        raise typer.Exit(1)


@app.command()
def fix(
    # Quality tool flags
    ruff: bool = typer.Option(True, "--ruff/--no-ruff", help="Enable/disable Ruff linting"),
    mypy: bool = typer.Option(True, "--mypy/--no-mypy", help="Enable/disable MyPy type checking"),
    drill_sergeant: bool = typer.Option(
        False, "--drill-sergeant/--no-drill-sergeant", help="Enable/disable Drill Sergeant"
    ),
    # File selection options (mutually exclusive)
    file: Path | None = typer.Option(None, "--file", "-f", help="Specific file to process"),
    files: str | None = typer.Option(
        None, "--files", help="Multiple files to process (comma-separated)"
    ),
    directory: Path | None = typer.Option(
        None, "--directory", "-d", help="Directory to process"
    ),
    pattern: str | None = typer.Option(
        None, "--pattern", help="Glob pattern to match files (e.g., 'src/**/*.py')"
    ),
    # Git-based filtering options
    git_changed: bool = typer.Option(
        False, "--git-changed", help="Only process changed (unstaged) files"
    ),
    git_staged: bool = typer.Option(
        False, "--git-staged", help="Only process staged files"
    ),
    git_diff: str | None = typer.Option(
        None, "--git-diff", help="Only process files changed vs specified branch (e.g., 'main')"
    ),
    # Advanced filtering options
    exclude: str | None = typer.Option(
        None, "--exclude", help="Exclusion patterns (comma-separated)"
    ),
    max_files: int | None = typer.Option(
        None, "--max-files", help="Maximum number of files to process"
    ),
    # Error filtering options
    error_type: str | None = typer.Option(
        None, "--error-type", help="Specific error types to fix (e.g., E501, F401)"
    ),
    ignore: str | None = typer.Option(
        None, "--ignore", help="Error codes to ignore (comma-separated)"
    ),
    # Processing options
    max_errors: int = typer.Option(100, "--max-errors", help="Maximum errors to fix per iteration"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be fixed without making changes"
    ),
    # Additional options
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """Fix code quality issues in your codebase."""

    if version:
        from stomper import __version__

        console.print(f"stomper v{__version__}")
        raise typer.Exit()

    # Validate file selection arguments
    validate_file_selection(file, files, directory, pattern, git_changed, git_staged, git_diff)

    # Load configuration
    try:
        project_root = Path.cwd()
        config_loader = ConfigLoader(project_root)
        # Load config (not used directly, but needed for validation)
        _ = config_loader.load_config()

        # Create CLI overrides
        cli_overrides = ConfigOverride(
            ruff=ruff,
            mypy=mypy,
            drill_sergeant=drill_sergeant,
            file=file,
            files=[Path(f.strip()) for f in files.split(",")] if files else None,
            directory=directory,
            error_type=error_type,
            ignore=[i.strip() for i in ignore.split(",")] if ignore else None,
            max_errors=max_errors,
            dry_run=dry_run,
            verbose=verbose,
        )

        # Validate CLI overrides
        validator = ConfigValidator()
        if not validator.validate_cli_overrides(cli_overrides):
            console.print("[red]Configuration validation failed[/red]")
            raise typer.Exit(1)

        # Apply CLI overrides to configuration
        final_config = config_loader.apply_cli_overrides(cli_overrides)

    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)

    # Print beautiful header
    print_header()
    
    # Prepare enabled tools list
    tools = []
    if ruff:
        tools.append("Ruff")
    if mypy:
        tools.append("MyPy")
    if drill_sergeant:
        tools.append("Drill Sergeant")
    
    # Print configuration summary
    config_dict = {
        "ai_agent": final_config.ai_agent,
        "max_retries": final_config.max_retries,
        "parallel_files": final_config.parallel_files,
    }
    print_config_summary(config_dict, tools, dry_run)

    # Initialize file discovery system
    file_scanner = FileScanner(project_root)

    # Get configuration settings for file discovery
    config_files = final_config.files

    # Implement precedence: CLI > config > defaults
    # Parse exclude patterns (CLI takes precedence)
    exclude_patterns = None
    if exclude:
        exclude_patterns = [p.strip() for p in exclude.split(",") if p.strip()]
    elif config_files.exclude:
        exclude_patterns = config_files.exclude

    # Get max files (CLI takes precedence)
    effective_max_files = max_files if max_files is not None else config_files.max_files_per_run

    # Discover files based on selection method
    target_info = ""
    if file:
        # Single file
        discovered_files = [file] if file.exists() else []
        target_info = f"Single file: {file}"
    elif files:
        # Multiple specific files
        file_list = [Path(f.strip()) for f in files.split(",") if f.strip()]
        discovered_files = [f for f in file_list if f.exists()]
        target_info = f"Multiple files: {len(discovered_files)} files"
    elif directory:
        # Directory scanning
        discovered_files = file_scanner.discover_files(
            target_path=directory,
            include_patterns=config_files.include,
            exclude_patterns=exclude_patterns,
            max_files=effective_max_files,
        )
        target_info = f"Directory: {directory}"
    elif pattern:
        # Glob pattern matching
        discovered_files = file_scanner.discover_files(
            target_path=Path(pattern),
            include_patterns=config_files.include,
            exclude_patterns=exclude_patterns,
            max_files=effective_max_files,
        )
        target_info = f"Pattern: {pattern}"
    elif git_changed or git_staged or git_diff:
        # Git-based file discovery
        from stomper.discovery.git import discover_git_files
        
        git_files = discover_git_files(
            project_root=project_root,
            git_changed=git_changed,
            git_staged=git_staged,
            git_diff=git_diff,
            python_only=True
        )
        
        # Convert to list and apply max_files limit
        discovered_files = list(git_files)
        if effective_max_files and len(discovered_files) > effective_max_files:
            discovered_files = discovered_files[:effective_max_files]
        
        # Generate target info
        if git_changed:
            target_info = "Changed (unstaged) files"
        elif git_staged:
            target_info = "Staged files"
        elif git_diff:
            target_info = f"Files changed vs {git_diff}"
        else:
            target_info = "Git-tracked files"
            
        # Print git summary
        from stomper.discovery.git import print_git_summary
        print_git_summary(set(discovered_files), git_changed, git_staged, git_diff)
    else:
        # Default: scan project root with config patterns
        discovered_files = file_scanner.discover_files(
            target_path=project_root,
            include_patterns=config_files.include,
            exclude_patterns=exclude_patterns,
            max_files=effective_max_files,
        )
        target_info = "All files in project root"

    # Show discovery results
    if discovered_files:
        stats = file_scanner.get_file_stats(discovered_files)
        print_file_discovery_summary(discovered_files, stats, target_info)
        
        if verbose:
            console.print(Panel("📁 Files to process:", box=box.ROUNDED, border_style="blue"))
            for f in discovered_files[:10]:  # Show first 10 files
                console.print(f"  {f.relative_to(project_root)}")
            if len(discovered_files) > 10:
                console.print(f"  ... and {len(discovered_files) - 10} more files")
            console.print()
    else:
        console.print(Panel("⚠️ No files found matching criteria", box=box.ROUNDED, border_style="yellow"))
        raise typer.Exit(0)

    # Initialize quality tool manager
    quality_manager = QualityToolManager()

    # Determine enabled tools from CLI arguments
    enabled_tools = []
    if ruff:
        enabled_tools.append("ruff")
    if mypy:
        enabled_tools.append("mypy")
    if drill_sergeant:
        enabled_tools.append("drill-sergeant")

    # Run quality tools with pattern-based processing
    console.print(Panel("🔍 Starting quality assessment...", box=box.ROUNDED, border_style="yellow"))

    try:
        # Use post-processing filtering (respects "don't surprise me" rule)
        all_errors = []

        if enabled_tools:
            # Step 1: Tools run with their own configurations (no Stomper pattern injection)
            all_errors = quality_manager.run_tools_with_patterns(
                include_patterns=[],  # Let tools use their own configs
                exclude_patterns=[],  # Let tools use their own configs
                project_root=project_root,
                enabled_tools=enabled_tools,
                max_errors=max_errors,
            )

            # Step 2: Apply Stomper's additional filtering (post-processing)
            if all_errors:
                all_errors = quality_manager.filter_results_with_stomper_patterns(
                    errors=all_errors,
                    include_patterns=config_files.include,
                    exclude_patterns=exclude_patterns,
                    project_root=project_root,
                )

        # Filter errors based on CLI arguments
        filtered_errors = all_errors

        if error_type:
            filtered_errors = quality_manager.filter_errors(
                filtered_errors, error_types=[error_type]
            )

        if ignore:
            ignore_list = [i.strip() for i in ignore.split(",")]
            filtered_errors = quality_manager.filter_errors(
                filtered_errors, ignore_codes=ignore_list
            )

        # Show beautiful results
        tool_summary = quality_manager.get_tool_summary(filtered_errors)
        print_quality_results(all_errors, filtered_errors, tool_summary, dry_run)

    except Exception as e:
        console.print(Panel(f"❌ Error during quality assessment: {e}", box=box.ROUNDED, border_style="red"))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
