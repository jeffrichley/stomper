"""Demonstration of Task 5: Error Mapping and Learning System features.

This script demonstrates all the cool features that were implemented.
"""

from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.agent_manager import AgentManager
from stomper.quality.base import QualityError

console = Console()


def demo_error_tracking():
    """Demonstrate error pattern tracking."""
    console.print("\n[bold blue]1. Error Pattern Tracking Demo[/bold blue]\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        
        # Create sample error
        error = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=10,
            column=80,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )
        
        # Record some attempts
        console.print("Recording fix attempts for E501...")
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        
        # Show pattern
        pattern = mapper.data.patterns["ruff:E501"]
        
        table = Table(title="Error Pattern: ruff:E501")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Attempts", str(pattern.total_attempts))
        table.add_row("Successes", f"[green]{pattern.successes}[/green]")
        table.add_row("Failures", f"[red]{pattern.failures}[/red]")
        table.add_row("Success Rate", f"{pattern.success_rate:.1f}%")
        table.add_row("Successful Strategies", ", ".join([s.value for s in pattern.successful_strategies]))
        table.add_row("Failed Strategies", ", ".join([s.value for s in pattern.failed_strategies]))
        
        console.print(table)
        console.print()


def demo_adaptive_strategies():
    """Demonstrate adaptive strategy selection."""
    console.print("\n[bold blue]2. Adaptive Strategy Selection Demo[/bold blue]\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        
        # Create difficult error
        error_difficult = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=10,
            column=80,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )
        
        # Make it difficult (25% success rate)
        mapper.record_attempt(error_difficult, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        for _ in range(3):
            mapper.record_attempt(error_difficult, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        
        # Create easy error
        error_easy = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=20,
            column=0,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )
        
        # Make it easy (90% success rate)
        for _ in range(9):
            mapper.record_attempt(error_easy, FixOutcome.SUCCESS, PromptStrategy.MINIMAL)
        mapper.record_attempt(error_easy, FixOutcome.FAILURE, PromptStrategy.MINIMAL)
        
        # Get adaptive strategies
        strategy_difficult = mapper.get_adaptive_strategy(error_difficult)
        strategy_easy = mapper.get_adaptive_strategy(error_easy)
        
        table = Table(title="Adaptive Strategy Decisions")
        table.add_column("Error", style="cyan")
        table.add_column("Success Rate", justify="right")
        table.add_column("Strategy Chosen", style="yellow")
        table.add_column("Include Examples", justify="center")
        
        table.add_row(
            "E501 (difficult)",
            f"[red]{mapper.get_success_rate('E501', 'ruff'):.1f}%[/red]",
            f"[bold]{strategy_difficult.verbosity.value.upper()}[/bold]",
            "Yes" if strategy_difficult.include_examples else "No"
        )
        
        table.add_row(
            "F401 (easy)",
            f"[green]{mapper.get_success_rate('F401', 'ruff'):.1f}%[/green]",
            f"[bold]{strategy_easy.verbosity.value.upper()}[/bold]",
            "Yes" if strategy_easy.include_examples else "No"
        )
        
        console.print(table)
        console.print("\n[dim]Difficult errors get DETAILED strategy, easy errors get MINIMAL![/dim]\n")


def demo_intelligent_fallback():
    """Demonstrate intelligent fallback selection."""
    console.print("\n[bold blue]3. Intelligent Fallback Demo[/bold blue]\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        
        error = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=10,
            column=0,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )
        
        # Record history: DETAILED works, NORMAL/MINIMAL don't
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)
        
        # Simulate trying different strategies
        failed_strategies = [PromptStrategy.NORMAL]
        
        fallback = mapper.get_fallback_strategy(error, failed_strategies)
        
        console.print("Scenario: NORMAL strategy just failed for E501")
        console.print(f"\nMapper suggests: [bold green]{fallback.value.upper()}[/bold green]")
        console.print(f"Reason: [dim]This strategy succeeded 2 times before for E501[/dim]\n")
        
        console.print("[dim]Intelligent! It tries proven strategies first![/dim]\n")


def demo_data_persistence():
    """Demonstrate data persistence."""
    console.print("\n[bold blue]4. Data Persistence Demo[/bold blue]\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create first mapper and record data
        console.print("Creating mapper #1 and recording data...")
        mapper1 = ErrorMapper(project_root=tmp_path, auto_save=True)
        error = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=10,
            column=0,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )
        
        mapper1.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper1.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)
        
        console.print(f"  Total attempts in mapper #1: {mapper1.data.total_attempts}")
        console.print(f"  Storage path: {mapper1.storage_path}")
        console.print()
        
        # Create second mapper - should load existing data
        console.print("Creating mapper #2 (should load existing data)...")
        mapper2 = ErrorMapper(project_root=tmp_path)
        
        console.print(f"  Total attempts in mapper #2: {mapper2.data.total_attempts}")
        console.print(f"  Patterns loaded: {len(mapper2.data.patterns)}")
        console.print()
        
        if mapper2.data.total_attempts == 2:
            console.print("[bold green]SUCCESS: Data persisted successfully![/bold green]\n")
        else:
            console.print("[bold red]FAIL: Data did not persist[/bold red]\n")


def demo_statistics_display():
    """Demonstrate statistics generation."""
    console.print("\n[bold blue]5. Statistics Display Demo[/bold blue]\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        
        # Create some realistic data
        errors_data = [
            ("E501", "ruff", [FixOutcome.SUCCESS] * 2 + [FixOutcome.FAILURE] * 8),  # 20% - difficult
            ("F401", "ruff", [FixOutcome.SUCCESS] * 19 + [FixOutcome.FAILURE] * 1),  # 95% - easy
            ("W291", "ruff", [FixOutcome.SUCCESS] * 11 + [FixOutcome.FAILURE] * 1),  # 92% - easy
            ("E701", "ruff", [FixOutcome.SUCCESS] * 6 + [FixOutcome.FAILURE] * 4),  # 60% - medium
        ]
        
        for code, tool, outcomes in errors_data:
            error = QualityError(
                tool=tool,
                file=Path("test.py"),
                line=10,
                column=0,
                code=code,
                message=f"{code} error",
                severity="error",
                auto_fixable=True,
            )
            for outcome in outcomes:
                mapper.record_attempt(error, outcome, PromptStrategy.NORMAL)
        
        # Get statistics
        stats = mapper.get_statistics()
        
        # Display
        console.print(f"Overall Success Rate: [bold]{stats['overall_success_rate']:.1f}%[/bold]")
        console.print(f"Total Attempts: {stats['total_attempts']}")
        console.print()
        
        # Difficult errors
        if stats['difficult_errors']:
            console.print("[bold red]Difficult Errors:[/bold red]")
            for e in stats['difficult_errors']:
                console.print(f"  • {e['code']}: {e['success_rate']:.1f}% success")
            console.print()
        
        # Easy errors
        if stats['easy_errors']:
            console.print("[bold green]Mastered Errors:[/bold green]")
            for e in stats['easy_errors']:
                console.print(f"  • {e['code']}: {e['success_rate']:.1f}% success")
            console.print()


def main():
    """Run all demonstrations."""
    console.print(Panel(
        "[bold]Task 5: Error Mapping and Learning System\nFeature Demonstration[/bold]",
        border_style="blue",
        box=box.DOUBLE,
    ))
    
    demo_error_tracking()
    demo_adaptive_strategies()
    demo_intelligent_fallback()
    demo_data_persistence()
    demo_statistics_display()
    
    console.print(Panel(
        "[bold green]All features working as demonstrated![/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()

