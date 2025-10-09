"""Main CLI entry point for Stomper."""

import sys
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import typer

from stomper.config.loader import ConfigLoader
from stomper.config.models import ConfigOverride
from stomper.config.validator import ConfigValidator
from stomper.discovery import FileScanner
from stomper.quality.manager import QualityToolManager

# Configure UTF-8 output for Windows emoji support
if sys.platform == "win32":
    try:
        # Reconfigure stdout/stderr to use UTF-8 encoding
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Fallback for older Python or terminals that don't support reconfigure
        pass

# Create the main Typer app
app = typer.Typer(
    name="stomper",
    help="Automated code quality fixing tool",
    add_completion=False,
)

# Create console for rich output with emoji support
# emoji=True converts :emoji_name: to actual emojis
# legacy_windows=False forces UTF-8 mode on Windows Terminal
console = Console(emoji=True, legacy_windows=False)


@app.command()
def stats(
    project_root: Path = typer.Option(
        Path.cwd(),
        "--project-root",
        "-p",
        help="Project root directory",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed statistics for all error patterns",
    ),
):
    """Display error mapping and learning statistics.

    Shows how well Stomper is learning to fix different error types,
    which errors are difficult, and which strategies work best.
    """
    try:
        from stomper.ai.mapper import ErrorMapper

        # Load mapper
        mapper = ErrorMapper(project_root=project_root)

        # Get statistics
        stats_data = mapper.get_statistics()

        console.print()

        # Display header
        header_panel = Panel(
            Align.center(Text("Stomper Learning Statistics", style="bold blue")),
            box=box.DOUBLE,
            border_style="blue",
            padding=(1, 2),
        )
        console.print(header_panel)
        console.print()

        # Overall stats
        overall_table = Table(title="Overall Performance", box=box.ROUNDED)
        overall_table.add_column("Metric", style="cyan", no_wrap=True)
        overall_table.add_column("Value", style="white")

        overall_rate = stats_data["overall_success_rate"]
        rate_color = "green" if overall_rate >= 70 else "yellow" if overall_rate >= 50 else "red"

        overall_table.add_row(
            "Overall Success Rate", f"[{rate_color}]{overall_rate:.1f}%[/{rate_color}]"
        )
        overall_table.add_row("Total Attempts", f"{stats_data['total_attempts']:,}")
        overall_table.add_row("Total Successes", f"{stats_data['total_successes']:,}")
        overall_table.add_row("Error Patterns Learned", str(stats_data["total_patterns"]))
        overall_table.add_row(
            "Last Updated", stats_data["last_updated"][:19] if stats_data["last_updated"] else "Never"
        )

        console.print(overall_table)
        console.print()

        # Difficult errors
        if stats_data["difficult_errors"]:
            difficult_table = Table(title="Needs Improvement", box=box.ROUNDED)
            difficult_table.add_column("Error", style="red", no_wrap=True)
            difficult_table.add_column("Tool", style="yellow")
            difficult_table.add_column("Success Rate", style="red", justify="right")
            difficult_table.add_column("Attempts", style="white", justify="right")

            for error in stats_data["difficult_errors"][:5]:  # Top 5
                difficult_table.add_row(
                    error["code"],
                    error["tool"],
                    f"{error['success_rate']:.1f}%",
                    str(error["attempts"]),
                )

            console.print(difficult_table)
            console.print()

            # Helpful tip
            console.print(
                "[dim italic]Tip: Difficult errors might benefit from better examples "
                "in the errors/ directory.[/dim italic]"
            )
            console.print()

        # Easy errors
        if stats_data["easy_errors"]:
            easy_table = Table(title="Mastered Errors", box=box.ROUNDED)
            easy_table.add_column("Error", style="green", no_wrap=True)
            easy_table.add_column("Tool", style="yellow")
            easy_table.add_column("Success Rate", style="green", justify="right")
            easy_table.add_column("Attempts", style="white", justify="right")

            for error in stats_data["easy_errors"][:5]:  # Top 5
                easy_table.add_row(
                    error["code"],
                    error["tool"],
                    f"{error['success_rate']:.1f}%",
                    str(error["attempts"]),
                )

            console.print(easy_table)
            console.print()

        # Verbose mode - show all patterns
        if verbose and mapper.data.patterns:
            all_table = Table(title="All Error Patterns", box=box.ROUNDED)
            all_table.add_column("Error", style="cyan")
            all_table.add_column("Tool", style="yellow")
            all_table.add_column("Success Rate", justify="right")
            all_table.add_column("Attempts", justify="right")
            all_table.add_column("Successes", style="green", justify="right")
            all_table.add_column("Failures", style="red", justify="right")

            for pattern_key, pattern in sorted(mapper.data.patterns.items()):
                rate_color = (
                    "green" if pattern.success_rate >= 70 else "yellow" if pattern.success_rate >= 50 else "red"
                )
                all_table.add_row(
                    pattern.error_code,
                    pattern.tool,
                    f"[{rate_color}]{pattern.success_rate:.1f}%[/{rate_color}]",
                    str(pattern.total_attempts),
                    str(pattern.successes),
                    str(pattern.failures),
                )

            console.print(all_table)
            console.print()

        # Storage location
        console.print(f"[dim]Data stored in: {mapper.storage_path}[/dim]")
        console.print()

        # No data message
        if stats_data["total_attempts"] == 0:
            console.print(
                Panel(
                    Align.center(Text("No learning data yet!\n\nRun 'stomper fix' to start learning.", style="yellow")),
                    box=box.ROUNDED,
                    border_style="yellow",
                )
            )
            console.print()

    except Exception as e:
        console.print(f"[red]Error loading statistics: {e}[/red]")
        raise typer.Exit(code=1)


def print_header() -> None:
    """Print a beautiful header for Stomper."""
    header_text = Text("Stomper", style="bold blue")
    subtitle = Text("Automated Code Quality Fixing", style="italic dim")

    header_panel = Panel(
        Align.center(Text.assemble(header_text, "\n", subtitle)),
        box=box.DOUBLE,
        border_style="blue",
        padding=(1, 2),
    )
    console.print(header_panel)
    console.print()


def print_config_summary(config: dict, enabled_tools: list, dry_run: bool) -> None:
    """Print a beautiful configuration summary."""
    # Create a table for configuration (using Rich emoji shortcode)
    table = Table(title=":wrench: Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    # Tool status (using Rich emoji shortcodes)
    tool_status = ":white_check_mark: " + ", ".join(enabled_tools) if enabled_tools else ":cross_mark: None"
    table.add_row("Enabled Tools", tool_status)

    # Dry run status (using Rich emoji shortcodes)
    dry_run_status = ":mag: Yes" if dry_run else ":zap: No"
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
    file_info.add_column(":file_folder: File Discovery", style="green", no_wrap=True)
    file_info.add_column("Value", style="white")

    file_info.add_row("Target", target_info)
    file_info.add_row("Files Found", f"{len(discovered_files):,}")
    file_info.add_row("Total Size", f"{stats['total_size']:,} bytes")
    file_info.add_row("Directories", str(len(stats["directories"])))

    console.print(file_info)
    console.print()


def print_quality_results(
    all_errors: list, filtered_errors: list, tool_summary: dict, dry_run: bool
) -> None:
    """Print beautiful quality assessment results."""
    if not filtered_errors:
        # No issues found
        success_panel = Panel(
            Align.center(Text(":party_popper: No matching issues found!", style="bold green")),
            box=box.ROUNDED,
            border_style="green",
            padding=(1, 2),
        )
        console.print(success_panel)
        return

    # Create results table
    results_table = Table(title=":mag: Quality Assessment Results", box=box.ROUNDED)
    results_table.add_column("Tool", style="cyan", no_wrap=True)
    results_table.add_column("Issues", style="red", justify="right")
    results_table.add_column("Status", style="yellow")

    for tool, count in tool_summary.items():
        status = ":mag: Dry Run" if dry_run else ":zap: Ready to Fix"
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
        title=":bar_chart: Summary",
        box=box.ROUNDED,
        border_style="red" if filtered_errors else "green",
    )
    console.print(summary_panel)

    if dry_run:
        console.print(
            Panel(":mag: Dry run complete - no changes made", box=box.ROUNDED, border_style="yellow")
        )
    else:
        console.print(
            Panel(
                ":zap: Quality tool integration complete!\n:wrench: Next: AI agent integration for automated fixing",
                box=box.ROUNDED,
                border_style="blue",
            )
        )


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
        console.print(
            "[yellow]Use one of: --file, --files, --directory, --pattern, --git-changed, --git-staged, or --git-diff[/yellow]"
        )
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
    directory: Path | None = typer.Option(None, "--directory", "-d", help="Directory to process"),
    pattern: str | None = typer.Option(
        None, "--pattern", help="Glob pattern to match files (e.g., 'src/**/*.py')"
    ),
    # Git-based filtering options
    git_changed: bool = typer.Option(
        False, "--git-changed", help="Only process changed (unstaged) files"
    ),
    git_staged: bool = typer.Option(False, "--git-staged", help="Only process staged files"),
    git_diff: str | None = typer.Option(
        None, "--git-diff", help="Only process files changed vs specified branch (e.g., 'main')"
    ),
    # Advanced filtering options
    include: str | None = typer.Option(
        None, "--include", help="Include patterns (comma-separated, e.g., '**/*.py,**/*.pyi')"
    ),
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
    max_errors: int = typer.Option(9999999, "--max-errors", help="Maximum errors to fix per iteration"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be fixed without making changes"
    ),
    # Workflow options (NEW - Phase 2 Parallel Processing)
    use_sandbox: bool = typer.Option(
        True, "--use-sandbox/--no-use-sandbox",
        help="Use git worktree sandbox for isolated execution (safer but slower)"
    ),
    run_tests: bool = typer.Option(
        True, "--run-tests/--no-run-tests",
        help="Run tests after fixes to validate no regressions"
    ),
    max_parallel_files: int = typer.Option(
        4, "--max-parallel-files",
        help="Maximum files to process in parallel (1=sequential, 4=balanced, 8+=fast)"
    ),
    test_validation: str = typer.Option(
        "full", "--test-validation",
        help="Test validation mode: full (all tests per file), quick (affected only), final (once at end), none (skip)"
    ),
    continue_on_error: bool = typer.Option(
        True, "--continue-on-error/--no-continue-on-error",
        help="Continue processing other files after a file fails"
    ),
    max_retries: int = typer.Option(
        3, "--max-retries",
        help="Maximum retry attempts per file"
    ),
    processing_strategy: str = typer.Option(
        "batch_errors", "--processing-strategy",
        help="Processing strategy: batch_errors, one_error_type, all_errors"
    ),
    agent_name: str = typer.Option(
        "cursor-cli", "--agent-name",
        help="AI agent to use for fixing"
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
            # Workflow overrides (NEW - Phase 2 Parallel Processing)
            use_sandbox=use_sandbox,
            run_tests=run_tests,
            max_retries=max_retries,
            processing_strategy=processing_strategy,
            agent_name=agent_name,
            test_validation=test_validation,
            continue_on_error=continue_on_error,
            max_parallel_files=max_parallel_files,
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

    # Implement precedence: CLI > context-based defaults > config defaults
    
    # Parse include patterns with proper precedence
    include_patterns = None
    if include:
        # CLI explicitly specified - highest priority
        include_patterns = [p.strip() for p in include.split(",") if p.strip()]
    elif directory:
        # User specified a directory - use sensible default for that directory
        include_patterns = ["**/*.py"]
    else:
        # Use config defaults (typically ["src/**/*.py", "tests/**/*.py"])
        include_patterns = config_files.include
    
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
        # Directory scanning with include patterns
        discovered_files = file_scanner.discover_files(
            target_path=directory,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_files=effective_max_files,
        )
        target_info = f"Directory: {directory}"
    elif pattern:
        # Glob pattern matching
        discovered_files = file_scanner.discover_files(
            target_path=Path(pattern),
            include_patterns=include_patterns,
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
            python_only=True,
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
        # Default: scan project root with include patterns
        discovered_files = file_scanner.discover_files(
            target_path=project_root,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_files=effective_max_files,
        )
        target_info = "All files in project root"

    # Show discovery results
    if discovered_files:
        stats = file_scanner.get_file_stats(discovered_files)
        print_file_discovery_summary(discovered_files, stats, target_info)

        if verbose:
            console.print(Panel(":file_folder: Files to process:", box=box.ROUNDED, border_style="blue"))
            for f in discovered_files[:10]:  # Show first 10 files
                console.print(f"  {f.relative_to(project_root)}")
            if len(discovered_files) > 10:
                console.print(f"  ... and {len(discovered_files) - 10} more files")
            console.print()
    else:
        console.print(
            Panel("⚠️ No files found matching criteria", box=box.ROUNDED, border_style="yellow")
        )
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
    console.print(
        Panel(":mag: Starting quality assessment...", box=box.ROUNDED, border_style="yellow")
    )

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
            # Use the SAME include_patterns we determined earlier (respects CLI/context/config precedence)
            if all_errors:
                all_errors = quality_manager.filter_results_with_stomper_patterns(
                    errors=all_errors,
                    include_patterns=include_patterns,  # Use precedence-aware patterns!
                    exclude_patterns=exclude_patterns or [],
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

        # If not dry run and errors found, invoke the workflow to fix them!
        if not dry_run and filtered_errors:
            console.print()
            console.print(
                Panel(
                    ":robot: Starting AI-powered workflow to fix issues...",
                    box=box.ROUNDED,
                    border_style="blue"
                )
            )
            
            # Import workflow components
            from stomper.workflow.orchestrator import StomperWorkflow
            from stomper.ai.agent_manager import AgentManager
            from stomper.ai.prompt_generator import PromptGenerator
            from stomper.ai.mapper import ErrorMapper
            from stomper.ai.sandbox_manager import SandboxManager
            from stomper.ai.cursor_client import CursorClient
            
            # Initialize workflow components
            agent_manager = AgentManager(project_root)
            prompt_generator = PromptGenerator()
            mapper = ErrorMapper(project_root)
            
            sandbox_manager = None
            if use_sandbox:
                sandbox_manager = SandboxManager(project_root)
            
            # Create workflow orchestrator
            workflow = StomperWorkflow(
                project_root=project_root,
                use_sandbox=use_sandbox,
                run_tests=run_tests,
                max_parallel_files=max_parallel_files,
            )
            
            # Register AI agent based on config
            if agent_name == "cursor-cli":
                try:
                    cursor_agent = CursorClient(
                        sandbox_manager=sandbox_manager,
                        timeout=60  # 60 seconds timeout for AI operations
                    )
                    workflow.register_agent("cursor-cli", cursor_agent)
                    console.print(f":robot: Registered agent: {agent_name}")
                except RuntimeError as e:
                    console.print(f"[red]:cross_mark: Failed to initialize {agent_name}: {e}[/red]")
                    raise typer.Exit(1)
            else:
                console.print(f"[red]:cross_mark: Unknown agent: {agent_name}[/red]")
                raise typer.Exit(1)
            
            # Build workflow config
            workflow_config = {
                "project_root": project_root,
                "enabled_tools": enabled_tools,
                "processing_strategy": processing_strategy,
                "max_errors_per_iteration": max_errors,
                "test_validation": test_validation,
                "continue_on_error": continue_on_error,
            }
            
            # Run the workflow asynchronously
            import asyncio
            
            try:
                console.print(":gear: Initializing workflow orchestrator...")
                result = asyncio.run(workflow.run(workflow_config))
                
                # Show final results
                console.print()
                console.print(
                    Panel(
                        f":white_check_mark: Workflow Complete!\n\n"
                        f"Successfully fixed: {len(result.get('successful_fixes', []))} files\n"
                        f"Failed: {len(result.get('failed_fixes', []))} files\n"
                        f"Total errors fixed: {result.get('total_errors_fixed', 0)}",
                        title=":party_popper: Results",
                        box=box.ROUNDED,
                        border_style="green"
                    )
                )
                
            except Exception as workflow_error:
                console.print(
                    Panel(
                        f":cross_mark: Workflow failed: {workflow_error}",
                        box=box.ROUNDED,
                        border_style="red"
                    )
                )
                raise typer.Exit(1)

    except Exception as e:
        console.print(
            Panel(f":cross_mark: Error during quality assessment: {e}", box=box.ROUNDED, border_style="red")
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
