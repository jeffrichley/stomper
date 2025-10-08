"""Quality tool manager for orchestrating multiple tools."""

from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .base import BaseQualityTool, QualityError
from .drill_sergeant import DrillSergeantTool
from .mypy import MyPyTool
from .pytest import PytestTool
from .ruff import RuffTool

console = Console()


class QualityToolManager:
    """Manages execution of multiple quality tools."""

    def __init__(self):
        """Initialize the quality tool manager."""
        self.tools: dict[str, BaseQualityTool] = {
            "ruff": RuffTool(),
            "mypy": MyPyTool(),
            "drill-sergeant": DrillSergeantTool(),
            "pytest": PytestTool(),
        }

    def get_available_tools(self) -> list[str]:
        """Get list of available quality tools.

        Returns:
            List of tool names that are available in PATH
        """
        return [name for name, tool in self.tools.items() if tool.is_available()]

    def run_tools(
        self, target_path: Path, project_root: Path, enabled_tools: list[str], max_errors: int = 100
    ) -> list[QualityError]:
        """Run enabled quality tools and collect errors.

        Args:
            target_path: Path to analyze (file or directory)
            project_root: Root directory of the project
            enabled_tools: List of tool names to run
            max_errors: Maximum number of errors to collect

        Returns:
            List of QualityError objects from all tools
        """
        all_errors = []

        # Filter to only available tools
        available_tools = [tool for tool in enabled_tools if tool in self.get_available_tools()]

        if not available_tools:
            console.print("[yellow]No quality tools are available in PATH[/yellow]")
            return []

        # Show which tools are available vs requested
        unavailable_tools = [tool for tool in enabled_tools if tool not in available_tools]
        if unavailable_tools:
            console.print(f"[yellow]Tools not available: {', '.join(unavailable_tools)}[/yellow]")

        console.print(f"[green]Running quality tools: {', '.join(available_tools)}[/green]")

        with Progress() as progress:
            task = progress.add_task("[blue]Running quality tools...", total=len(available_tools))

            for tool_name in available_tools:
                tool = self.tools[tool_name]

                try:
                    # Update progress bar with current tool name
                    progress.update(task, description=f"[blue]Running {tool_name}...[/blue]")

                    errors = tool.run_tool(target_path, project_root)

                    # Filter errors if we have too many
                    if len(errors) > max_errors:
                        errors = errors[:max_errors]

                    all_errors.extend(errors)

                except Exception as e:
                    console.print(f"[red]Error running {tool_name}: {e}[/red]")

                progress.update(task, advance=1)

        console.print(f"[blue]Quality tools found {len(all_errors)} total issues[/blue]")
        return all_errors

    def run_tools_with_patterns(
        self,
        include_patterns: list[str],
        exclude_patterns: list[str],
        project_root: Path,
        enabled_tools: list[str],
        max_errors: int = 100,
    ) -> list[QualityError]:
        """Run enabled quality tools with pattern-based discovery.

        Args:
            include_patterns: Patterns to include for file discovery
            exclude_patterns: Patterns to exclude for file discovery
            project_root: Root directory of the project
            enabled_tools: List of tool names to run
            max_errors: Maximum number of errors to collect

        Returns:
            List of QualityError objects from all tools
        """
        all_errors = []

        # Filter to only available tools
        available_tools = [tool for tool in enabled_tools if tool in self.get_available_tools()]

        if not available_tools:
            console.print("[yellow]No quality tools are available in PATH[/yellow]")
            return []

        # Show which tools are available vs requested
        unavailable_tools = [tool for tool in enabled_tools if tool not in available_tools]
        if unavailable_tools:
            console.print(f"[yellow]Tools not available: {', '.join(unavailable_tools)}[/yellow]")

        console.print(
            f"[green]Running quality tools with patterns: {', '.join(available_tools)}[/green]"
        )
        console.print(f"[blue]Include patterns: {', '.join(include_patterns)}[/blue]")
        if exclude_patterns:
            console.print(f"[blue]Exclude patterns: {', '.join(exclude_patterns)}[/blue]")

        # Pre-discover configurations to avoid progress bar interference
        tool_configs = {}
        for tool_name in available_tools:
            tool = self.tools[tool_name]
            config_file = tool.discover_tool_config(project_root)
            if config_file:
                console.print(f"[blue]🔧 {tool_name}: Using config from {config_file.name}[/blue]")
            else:
                console.print(
                    f"[yellow]⚠️  {tool_name}: No config found, using Stomper baseline[/yellow]"
                )
            tool_configs[tool_name] = config_file

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            expand=True,
        ) as progress:
            task = progress.add_task("🔧 Running quality tools...", total=len(available_tools))

            for tool_name in available_tools:
                tool = self.tools[tool_name]

                try:
                    # Update progress bar with current tool name
                    progress.update(task, description=f"🔧 Running {tool_name}...")

                    # Use pattern-based execution
                    errors = tool.run_tool_with_patterns(
                        include_patterns=include_patterns,
                        exclude_patterns=exclude_patterns,
                        project_root=project_root,
                    )

                    # Filter errors if we have too many
                    if len(errors) > max_errors:
                        errors = errors[:max_errors]

                    all_errors.extend(errors)

                except Exception as e:
                    console.print(f"[red]Error running {tool_name}: {e}[/red]")

                progress.update(task, advance=1)

        console.print(f"[blue]Quality tools found {len(all_errors)} total issues[/blue]")
        return all_errors

    def filter_results_with_stomper_patterns(
        self,
        errors: list[QualityError],
        include_patterns: list[str],
        exclude_patterns: list[str],
        project_root: Path,
    ) -> list[QualityError]:
        """Filter results using Stomper's patterns (post-processing filtering).

        This implements the "don't surprise me" rule by applying Stomper's
        additional filtering after tools have run with their own configurations.

        Args:
            errors: List of QualityError objects from tools
            include_patterns: Stomper include patterns
            exclude_patterns: Stomper exclude patterns
            project_root: Root directory of the project

        Returns:
            Filtered list of QualityError objects
        """
        if not errors:
            return []

        # Import pathspec for pattern matching
        import pathspec

        # Create pathspec objects for pattern matching
        include_spec = None
        if include_patterns:
            include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)

        exclude_spec = None
        if exclude_patterns:
            exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)

        filtered_errors = []

        for error in errors:
            # Get relative path for pattern matching
            try:
                relative_path = error.file.relative_to(project_root)
                relative_path_str = str(relative_path)
            except ValueError:
                # File is outside project root, skip it
                continue

            # Check include patterns
            if include_spec and not include_spec.match_file(relative_path_str):
                continue

            # Check exclude patterns
            if exclude_spec and exclude_spec.match_file(relative_path_str):
                continue

            # File passed all filters
            filtered_errors.append(error)

        return filtered_errors

    def get_tool_summary(self, errors: list[QualityError]) -> dict[str, int]:
        """Get summary of errors by tool.

        Args:
            errors: List of QualityError objects

        Returns:
            Dictionary mapping tool names to error counts
        """
        summary: dict[str, int] = {}
        for error in errors:
            summary[error.tool] = summary.get(error.tool, 0) + 1
        return summary

    def filter_errors(
        self,
        errors: list[QualityError],
        error_types: list[str] | None = None,
        ignore_codes: list[str] | None = None,
        files: list[Path] | None = None,
    ) -> list[QualityError]:
        """Filter errors based on criteria.

        Args:
            errors: List of QualityError objects to filter
            error_types: List of error types to include (e.g., ['E501', 'F401'])
            ignore_codes: List of error codes to ignore
            files: List of files to include (if None, include all files)

        Returns:
            Filtered list of QualityError objects
        """
        filtered = errors

        # Filter by error types
        if error_types:
            filtered = [e for e in filtered if e.code in error_types]

        # Filter out ignored codes
        if ignore_codes:
            filtered = [e for e in filtered if e.code not in ignore_codes]

        # Filter by files
        if files:
            file_paths = set(files)
            filtered = [e for e in filtered if e.file in file_paths]

        return filtered
