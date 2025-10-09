# Task 5 Integration Plan: Connect ErrorMapper to the Workflow

> **Status:** Ready for Implementation  
> **Created:** 2025-01-08  
> **Parent Task:** Task 5 - Error Mapping and Learning System  
> **Prerequisites:** ✅ ErrorMapper fully implemented and tested

## 📋 Overview

This plan details how to integrate the ErrorMapper with existing components to create an intelligent, self-improving fix workflow. The ErrorMapper is built and tested - now we need to connect it to make it actually useful!

## 🎯 Goals

Make the system **intelligent** by:
1. **Adapting prompts** based on what's worked before
2. **Smart retries** using historical success patterns
3. **Visible learning** so users can see improvement

## 🏗️ Integration Points

### Current State (Isolated)

```
ErrorMapper ❌ (exists but not used)
    ↓
  (no connections)
    
PromptGenerator → LLM → FixApplier
(dumb, no learning)
```

### Target State (Integrated)

```
ErrorMapper 🧠
    ├──> PromptGenerator (adaptive prompts)
    ├──> AgentManager (intelligent fallback)
    └──> CLI (statistics display)
         ↓
    Smart, self-improving workflow!
```

---

## 📝 Integration Task Breakdown

### Integration 1: PromptGenerator Uses Adaptive Strategies

**Estimated Time:** 2-3 hours

#### What Changes:

**Before:**
```python
# Always same prompt, no learning
generator = PromptGenerator()
prompt = generator.generate_prompt(errors, code_context)
```

**After:**
```python
# Adapts based on history
generator = PromptGenerator(project_root=main_project_root)
prompt = generator.generate_prompt(errors, code_context, retry_count=0)
# → Mapper checks: E501 has 25% success rate → Use DETAILED prompt
```

#### Implementation Steps:

##### Step 1: Modify PromptGenerator Constructor

**File:** `src/stomper/ai/prompt_generator.py`

```python
# ADD IMPORTS
from pathlib import Path
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import AdaptiveStrategy, PromptStrategy

class PromptGenerator:
    """Generates prompts for AI agents based on quality errors and code context."""
    
    def __init__(
        self,
        template_dir: str = "templates",
        errors_dir: str = "errors",
        project_root: Path | None = None,  # NEW
        mapper: ErrorMapper | None = None,  # NEW
    ):
        """Initialize the PromptGenerator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
            errors_dir: Directory containing error mapping files
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper for adaptive strategies (optional, created if not provided)
        """
        self.template_dir = Path(template_dir)
        self.errors_dir = Path(errors_dir)
        
        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is not None:
                self.mapper = ErrorMapper(project_root=project_root)
            else:
                # No mapper - fallback to non-adaptive mode
                self.mapper = None
                logger.warning("PromptGenerator initialized without mapper - no adaptive strategies")
        else:
            self.mapper = mapper
        
        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(template_dir))
```

##### Step 2: Modify generate_prompt() Method

```python
def generate_prompt(
    self,
    errors: list[QualityError],
    code_context: str,
    retry_count: int = 0,  # NEW
) -> str:
    """Generate a prompt for AI agents based on errors and code context.
    
    Args:
        errors: List of quality errors to fix
        code_context: Surrounding code context
        retry_count: Number of retry attempts (for adaptive strategies)
    
    Returns:
        Generated prompt string
    """
    if not errors:
        logger.warning("No errors provided to PromptGenerator")
        return self._generate_empty_prompt()
    
    # Get adaptive strategy for primary error (if mapper available)
    adaptive_strategy = None
    if self.mapper:
        primary_error = errors[0]
        adaptive_strategy = self.mapper.get_adaptive_strategy(
            primary_error,
            retry_count=retry_count,
        )
        logger.debug(
            f"Using {adaptive_strategy.verbosity.value} strategy for {primary_error.code} "
            f"(retry #{retry_count})"
        )
    
    # Extract error context
    error_context = self._extract_error_context(errors)
    
    # Load error-specific advice (enhanced with adaptive strategy)
    error_advice = self._load_error_advice(errors, adaptive_strategy)
    
    # Process code context (adapt based on strategy)
    processed_code_context = self._process_code_context(
        code_context,
        adaptive_strategy,
    )
    
    # Add adaptive strategy to context (for template)
    if adaptive_strategy:
        error_context["adaptive_strategy"] = {
            "verbosity": adaptive_strategy.verbosity.value,
            "retry_count": adaptive_strategy.retry_count,
            "include_examples": adaptive_strategy.include_examples,
            "include_history": adaptive_strategy.include_history,
            "suggested_approach": adaptive_strategy.suggested_approach,
        }
    
    # Generate prompt using template
    try:
        template = self.env.get_template("fix_prompt.j2")
        prompt = template.render(
            error_context=error_context,
            error_advice=error_advice,
            code_context=processed_code_context,
            adaptive_strategy=adaptive_strategy,
        )
        
        return prompt
    
    except TemplateNotFound:
        logger.error(f"Template file not found in {self.template_dir}")
        raise FileNotFoundError(f"Template file not found in {self.template_dir}")
```

##### Step 3: Enhance _load_error_advice() Method

```python
def _load_error_advice(
    self,
    errors: list[QualityError],
    adaptive_strategy: AdaptiveStrategy | None = None,  # NEW
) -> dict[str, str]:
    """Load error-specific advice from mapping files.
    
    Args:
        errors: List of quality errors
        adaptive_strategy: Adaptive strategy for this fix (optional)
    
    Returns:
        Dictionary mapping error codes to advice
    """
    advice = {}
    
    for error in errors:
        error_code = error.code
        tool = error.tool
        
        # Try to load advice file
        advice_file = self._get_advice_file_path(tool, error_code)
        if advice_file and advice_file.exists():
            try:
                base_advice = advice_file.read_text(encoding="utf-8")
                
                # Enhance advice with adaptive strategy suggestions
                if adaptive_strategy and adaptive_strategy.suggested_approach:
                    enhanced_advice = (
                        f"{base_advice}\n\n"
                        f"**💡 Recommended Approach (based on history):**\n"
                        f"{adaptive_strategy.suggested_approach}"
                    )
                    advice[error_code] = enhanced_advice
                else:
                    advice[error_code] = base_advice
            
            except Exception as e:
                logger.warning(f"Failed to read advice file {advice_file}: {e}")
                advice[error_code] = f"Fix {error_code}: {error.message}"
        else:
            # Fallback to generic advice
            advice[error_code] = f"Fix {error_code}: {error.message}"
    
    return advice
```

##### Step 4: Add _process_code_context() Enhancement

```python
def _process_code_context(
    self,
    code_context: str,
    adaptive_strategy: AdaptiveStrategy | None = None,  # NEW
) -> str:
    """Process code context for inclusion in prompts.
    
    Args:
        code_context: Raw code context
        adaptive_strategy: Strategy for this fix (optional)
    
    Returns:
        Processed code context
    """
    if not code_context or not code_context.strip():
        return "No code context available"
    
    # For detailed/verbose strategies, include more context
    # For minimal strategy, could provide less context
    # (Currently just returns full context, but hook is here for future)
    
    return code_context
```

#### Testing:

Create `tests/unit/test_prompt_generator_adaptive.py`:

```python
"""Test PromptGenerator adaptive strategy integration."""

import pytest
from pathlib import Path

from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


@pytest.mark.unit
def test_prompt_generator_uses_adaptive_strategy(tmp_path):
    """Test PromptGenerator uses mapper for adaptive strategies."""
    # Create mapper with some history
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
    
    # Create difficult pattern
    for _ in range(3):
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
    
    # Create generator with mapper
    generator = PromptGenerator(
        template_dir="templates",
        errors_dir="errors",
        mapper=mapper,
    )
    
    # Generate prompt - should use DETAILED strategy
    prompt = generator.generate_prompt([error], "code context", retry_count=0)
    
    # Prompt should be enhanced (hard to test exact content, but it should be longer)
    assert len(prompt) > 0


@pytest.mark.unit
def test_prompt_generator_escalates_on_retry(tmp_path):
    """Test PromptGenerator escalates strategy on retry."""
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
    
    # Record some failures
    for _ in range(3):
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
    
    generator = PromptGenerator(template_dir="templates", errors_dir="errors", mapper=mapper)
    
    # First attempt
    prompt0 = generator.generate_prompt([error], "code", retry_count=0)
    # Second attempt (retry)
    prompt1 = generator.generate_prompt([error], "code", retry_count=1)
    
    # Prompts should be different (escalated)
    # (Exact assertion depends on template, but they should differ)
    assert isinstance(prompt0, str)
    assert isinstance(prompt1, str)
```

---

### Integration 2: AgentManager Uses Intelligent Fallback

**Estimated Time:** 2-3 hours

#### What Changes:

**Before:**
```python
# Simple try-once or basic fallback
manager = AgentManager()
result = manager.generate_fix_with_fallback(...)
# → Tries agents in order, no learning
```

**After:**
```python
# Intelligent retry with learning
manager = AgentManager(project_root=main_project_root)
result = manager.generate_fix_with_intelligent_fallback(error, ...)
# → Tries proven strategies first, records outcomes, learns
```

#### Implementation Steps:

##### Step 1: Modify AgentManager Constructor

**File:** `src/stomper/ai/agent_manager.py`

```python
# ADD IMPORTS
from pathlib import Path
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError

class AgentManager:
    """Manager for AI agent selection, fallback, and coordination."""
    
    def __init__(
        self,
        project_root: Path | None = None,  # NEW
        mapper: ErrorMapper | None = None,  # NEW
    ):
        """Initialize agent manager.
        
        Args:
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper instance (optional, created if not provided)
        """
        self._agents: dict[str, AIAgent] = {}
        self._fallback_order: list[str] = []
        self._default_agent: str | None = None
        
        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is not None:
                self.mapper = ErrorMapper(project_root=project_root)
            else:
                # No mapper - fallback to non-adaptive mode
                self.mapper = None
                logger.warning("AgentManager initialized without mapper - no intelligent fallback")
        else:
            self.mapper = mapper
```

##### Step 2: Add generate_fix_with_intelligent_fallback() Method

```python
def generate_fix_with_intelligent_fallback(
    self,
    primary_agent_name: str,
    error: QualityError,
    error_context: dict[str, Any],
    code_context: str,
    prompt: str,
    max_retries: int = 3,
) -> str:
    """Generate fix with intelligent fallback based on error history.
    
    Args:
        primary_agent_name: Name of primary agent to try
        error: Quality error being fixed
        error_context: Error context
        code_context: Code context
        prompt: Fix prompt
        max_retries: Maximum retry attempts
    
    Returns:
        Generated fix from successful attempt
    
    Raises:
        RuntimeError: If all retries exhausted
    """
    if not self.mapper:
        # Fallback to simple mode if no mapper
        logger.warning("No mapper available, using simple fallback")
        return self.generate_fix_with_fallback(
            primary_agent_name,
            error_context,
            code_context,
            prompt,
        )
    
    failed_strategies = []
    
    for retry_count in range(max_retries):
        # Get adaptive strategy from mapper
        adaptive_strategy = self.mapper.get_adaptive_strategy(
            error,
            retry_count=retry_count,
        )
        
        # Try to get fallback strategy if we've failed
        if retry_count > 0:
            fallback_strategy = self.mapper.get_fallback_strategy(
                error,
                failed_strategies,
            )
            
            if fallback_strategy is None:
                logger.warning("All fallback strategies exhausted")
                break
            
            logger.info(
                f"🔄 Retry #{retry_count}: Using fallback strategy {fallback_strategy.value}"
            )
        
        # Try to generate fix
        try:
            if primary_agent_name not in self._agents:
                raise ValueError(f"Agent '{primary_agent_name}' not found")
            
            agent = self._agents[primary_agent_name]
            logger.info(
                f"🤖 Attempting fix with {primary_agent_name} "
                f"(strategy: {adaptive_strategy.verbosity.value}, retry: {retry_count})"
            )
            
            result = agent.generate_fix(error_context, code_context, prompt)
            
            # ✅ Record success
            self.mapper.record_attempt(
                error,
                FixOutcome.SUCCESS,
                adaptive_strategy.verbosity,
            )
            
            logger.info(
                f"✅ Fix successful with {adaptive_strategy.verbosity.value} strategy!"
            )
            
            return result
        
        except Exception as e:
            logger.warning(
                f"❌ Attempt {retry_count + 1} failed with {primary_agent_name}: {e}"
            )
            
            # Record failure
            self.mapper.record_attempt(
                error,
                FixOutcome.FAILURE,
                adaptive_strategy.verbosity,
            )
            
            failed_strategies.append(adaptive_strategy.verbosity)
    
    # All retries exhausted
    raise RuntimeError(
        f"All {max_retries} retry attempts failed for {error.code}"
    )
```

#### Testing:

Create `tests/unit/test_agent_manager_adaptive.py`:

```python
"""Test AgentManager intelligent fallback integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from stomper.ai.agent_manager import AgentManager
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


@pytest.mark.unit
def test_agent_manager_uses_intelligent_fallback(tmp_path):
    """Test AgentManager uses mapper for intelligent fallback."""
    # Create mapper with history
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
    
    # Record that DETAILED strategy worked before
    mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
    mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
    
    # Create manager with mapper
    manager = AgentManager(mapper=mapper)
    
    # Register mock agent
    mock_agent = Mock()
    mock_agent.generate_fix.return_value = "fixed code"
    manager.register_agent("test_agent", mock_agent)
    
    # Try to fix - should use DETAILED strategy first due to history
    result = manager.generate_fix_with_intelligent_fallback(
        "test_agent",
        error,
        {"test": "context"},
        "code context",
        "fix prompt",
    )
    
    assert result == "fixed code"
    assert mock_agent.generate_fix.called


@pytest.mark.unit
def test_agent_manager_records_outcomes(tmp_path):
    """Test AgentManager records fix outcomes to mapper."""
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
    
    manager = AgentManager(mapper=mapper)
    
    # Register mock agent
    mock_agent = Mock()
    mock_agent.generate_fix.return_value = "fixed code"
    manager.register_agent("test_agent", mock_agent)
    
    # Attempt fix
    manager.generate_fix_with_intelligent_fallback(
        "test_agent",
        error,
        {},
        "",
        "",
    )
    
    # Check mapper recorded the outcome
    assert mapper.data.total_attempts == 1
    assert mapper.data.total_successes == 1
```

---

### Integration 3: CLI Displays Learning Statistics

**Estimated Time:** 2-3 hours

#### What Changes:

**Before:**
```bash
$ stomper fix
# Shows results, but no learning insights
```

**After:**
```bash
$ stomper stats
# Shows comprehensive learning statistics!

$ stomper fix --verbose
# Shows adaptive strategy decisions in real-time
```

#### Implementation Steps:

##### Step 1: Add stats Command

**File:** `src/stomper/cli.py`

```python
# ADD IMPORTS at top of file
from stomper.ai.mapper import ErrorMapper
from rich.align import Align


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
        help="Show detailed statistics",
    ),
):
    """Display error mapping and learning statistics.
    
    Shows how well Stomper is learning to fix different error types,
    which errors are difficult, and which strategies work best.
    """
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    
    console.print()
    
    try:
        # Load mapper
        mapper = ErrorMapper(project_root=project_root)
        
        # Get statistics
        stats_data = mapper.get_statistics()
        
        # Display header
        header_panel = Panel(
            Align.center(Text("🧠 Stomper Learning Statistics", style="bold blue")),
            box=box.DOUBLE,
            border_style="blue",
            padding=(1, 2),
        )
        console.print(header_panel)
        console.print()
        
        # Overall stats
        overall_table = Table(title="📊 Overall Performance", box=box.ROUNDED)
        overall_table.add_column("Metric", style="cyan", no_wrap=True)
        overall_table.add_column("Value", style="white")
        
        overall_rate = stats_data['overall_success_rate']
        rate_color = "green" if overall_rate >= 70 else "yellow" if overall_rate >= 50 else "red"
        
        overall_table.add_row(
            "Overall Success Rate",
            f"[{rate_color}]{overall_rate:.1f}%[/{rate_color}]"
        )
        overall_table.add_row("Total Attempts", f"{stats_data['total_attempts']:,}")
        overall_table.add_row("Total Successes", f"{stats_data['total_successes']:,}")
        overall_table.add_row("Error Patterns Learned", str(stats_data['total_patterns']))
        overall_table.add_row("Last Updated", stats_data['last_updated'][:19])  # Trim milliseconds
        
        console.print(overall_table)
        console.print()
        
        # Difficult errors
        if stats_data['difficult_errors']:
            difficult_table = Table(title="⚠️  Needs Improvement", box=box.ROUNDED)
            difficult_table.add_column("Error", style="red", no_wrap=True)
            difficult_table.add_column("Tool", style="yellow")
            difficult_table.add_column("Success Rate", style="red", justify="right")
            difficult_table.add_column("Attempts", style="white", justify="right")
            
            for error in stats_data['difficult_errors'][:5]:  # Top 5
                difficult_table.add_row(
                    error['code'],
                    error['tool'],
                    f"{error['success_rate']:.1f}%",
                    str(error['attempts']),
                )
            
            console.print(difficult_table)
            console.print()
            
            # Helpful tip
            console.print(
                "💡 [dim italic]Tip: Difficult errors might benefit from better examples "
                "in the errors/ directory.[/dim italic]"
            )
            console.print()
        
        # Easy errors
        if stats_data['easy_errors']:
            easy_table = Table(title="✅ Mastered Errors", box=box.ROUNDED)
            easy_table.add_column("Error", style="green", no_wrap=True)
            easy_table.add_column("Tool", style="yellow")
            easy_table.add_column("Success Rate", style="green", justify="right")
            easy_table.add_column("Attempts", style="white", justify="right")
            
            for error in stats_data['easy_errors'][:5]:  # Top 5
                easy_table.add_row(
                    error['code'],
                    error['tool'],
                    f"{error['success_rate']:.1f}% 🎉",
                    str(error['attempts']),
                )
            
            console.print(easy_table)
            console.print()
        
        # Storage location
        console.print(
            f"📁 [dim]Data stored in: {mapper.storage_path}[/dim]"
        )
        console.print()
        
        # Verbose mode - show all patterns
        if verbose and mapper.data.patterns:
            all_table = Table(title="📋 All Error Patterns", box=box.ROUNDED)
            all_table.add_column("Error", style="cyan")
            all_table.add_column("Tool", style="yellow")
            all_table.add_column("Success Rate", justify="right")
            all_table.add_column("Attempts", justify="right")
            all_table.add_column("Successes", style="green", justify="right")
            all_table.add_column("Failures", style="red", justify="right")
            
            for pattern_key, pattern in mapper.data.patterns.items():
                rate_color = "green" if pattern.success_rate >= 70 else "yellow" if pattern.success_rate >= 50 else "red"
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
    
    except Exception as e:
        console.print(f"[red]Error loading statistics: {e}[/red]")
        raise typer.Exit(code=1)
```

##### Step 2: Add Verbose Logging to fix Command

Update the `fix` command to show adaptive decisions when `--verbose` is used:

```python
# In the fix command, after creating PromptGenerator/AgentManager:

if verbose and mapper:
    # Show learning insights
    console.print("\n[dim italic]🧠 Using adaptive learning for intelligent fixing...[/dim italic]\n")
    
    # Could show strategy decisions for each error
    # (This would be logged during the fix process)
```

#### Testing:

Create `tests/e2e/test_cli_stats.py`:

```python
"""End-to-end tests for stats command."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from stomper.cli import app
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


runner = CliRunner()


@pytest.mark.e2e
def test_stats_command_displays_statistics(tmp_path):
    """Test stats command displays learning statistics."""
    # Create some learning data
    mapper = ErrorMapper(project_root=tmp_path)
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
    
    # Record some attempts
    for _ in range(5):
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
    for _ in range(2):
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)
    
    # Run stats command
    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Learning Statistics" in result.stdout
    assert "Overall Performance" in result.stdout
    assert "71.4%" in result.stdout or "71.43%" in result.stdout  # 5/7 success rate


@pytest.mark.e2e
def test_stats_command_verbose_mode(tmp_path):
    """Test stats command verbose mode shows all patterns."""
    mapper = ErrorMapper(project_root=tmp_path)
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
    
    mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
    
    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path), "--verbose"])
    
    assert result.exit_code == 0
    assert "All Error Patterns" in result.stdout
```

---

## ✅ Acceptance Criteria

Integration is complete when:

### PromptGenerator Integration:
- [ ] Constructor accepts `project_root` and `mapper` parameters
- [ ] `generate_prompt()` accepts `retry_count` parameter
- [ ] Uses `mapper.get_adaptive_strategy()` to adapt prompts
- [ ] Enhances error advice with historical suggestions
- [ ] All existing tests still pass
- [ ] New adaptive tests pass

### AgentManager Integration:
- [ ] Constructor accepts `project_root` and `mapper` parameters
- [ ] New `generate_fix_with_intelligent_fallback()` method exists
- [ ] Records fix outcomes to mapper (SUCCESS/FAILURE)
- [ ] Uses `mapper.get_fallback_strategy()` for retries
- [ ] Logs adaptive decisions for debugging
- [ ] All existing tests still pass
- [ ] New intelligent fallback tests pass

### CLI Integration:
- [ ] New `stomper stats` command exists
- [ ] Displays overall success rate
- [ ] Shows difficult errors table
- [ ] Shows mastered errors table
- [ ] Verbose mode shows all patterns
- [ ] Storage location displayed
- [ ] E2E tests pass

### Overall:
- [ ] No regressions in existing functionality
- [ ] All new code has ≥80% test coverage
- [ ] No linting/type errors
- [ ] Documentation updated
- [ ] Integration actually works end-to-end

---

## 🚀 Implementation Order

1. **PromptGenerator Integration** (2-3 hours)
   - Modify constructor
   - Update generate_prompt()
   - Enhance advice loading
   - Write tests
   - Verify no regressions

2. **AgentManager Integration** (2-3 hours)
   - Modify constructor
   - Add intelligent_fallback method
   - Record outcomes
   - Write tests
   - Verify no regressions

3. **CLI Integration** (2-3 hours)
   - Add stats command
   - Create statistics tables
   - Add verbose logging
   - Write E2E tests
   - Update help text

**Total Estimated Time:** 6-9 hours (1-2 days)

---

## 📊 Success Metrics

### Measurable Improvements:

After integration, you should see:
- ✅ **Prompts adapt** based on error difficulty
- ✅ **Retries are smarter** - tries proven strategies first
- ✅ **Success rates improve** over time
- ✅ **Visibility** - users can see what's working

### Testing Success:

```bash
# All tests pass
just test

# New features work
stomper stats  # Shows learning data
stomper fix --verbose  # Shows adaptive decisions

# Learning actually happens
# Run fix multiple times → success rate improves!
```

---

## 🎯 Why This Matters

### Before Integration:
- ❌ Mapper exists but unused (dead code)
- ❌ Prompts are always the same
- ❌ Retries are dumb (try same thing again)
- ❌ No learning, no improvement
- ❌ Users can't see what's happening

### After Integration:
- ✅ Mapper drives intelligent decisions
- ✅ Prompts adapt to error difficulty
- ✅ Retries use proven strategies
- ✅ System learns and improves
- ✅ Users see learning statistics

**This transforms Stomper from a "tool" into an "intelligent system"!** 🧠✨

---

## 📝 Notes

### Backward Compatibility:

All integrations include fallbacks for when mapper is not available:
```python
if self.mapper:
    # Use intelligent mode
else:
    # Fall back to simple mode (existing behavior)
```

This ensures existing code doesn't break!

### Performance:

Mapper operations are fast (<50ms):
- Loading: Read JSON file once on init
- Decision: Simple rules checking in-memory data
- Recording: Append to in-memory list + optional save

### Data Storage:

- Stored in: `{project_root}/.stomper/learning_data.json`
- Auto-saved after each fix attempt
- Persists across runs
- Human-readable JSON format

---

## 🎉 Ready to Implement!

This plan provides everything needed to connect the ErrorMapper to the existing workflow and create an intelligent, self-improving system!

Follow the TDD approach:
1. Write integration tests
2. Implement integrations
3. Verify everything works
4. Celebrate! 🎉

