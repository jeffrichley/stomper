# Stomper MVP Technical Specification

## Overview
Automated code quality fixing tool that systematically resolves linting errors, type errors, and test failures using AI agents while maintaining code integrity.

## Core Features

### 1. Quality Assessment Engine
- **Direct tool execution**: ruff, mypy, drill-sergeant, pytest
- **JSON output parsing**: Structured error collection
- **Configuration respect**: Uses existing pyproject.toml settings
- **Error grouping**: Organizes by file and error type

### 2. AI Agent Integration
- **Cursor CLI headless mode**: Primary AI agent
- **Structured prompts**: Error-specific advice generation
- **File-level processing**: One file at a time for precision
- **Response validation**: Verify fixes actually resolved issues

### 3. Testing & Validation
- **Pytest integration**: Run tests after each fix
- **Fix verification**: Re-run quality tools to confirm resolution
- **Rollback capability**: Git-based recovery mechanisms
- **Flaky test handling**: Retry logic for unreliable tests

### 4. Git Integration
- **Session branches**: `stomper/auto-fixes-{timestamp}`
- **Atomic commits**: One commit per successfully fixed file
- **Conventional commits**: Standardized commit messages
- **Rollback support**: Easy recovery from failed fixes

## Technical Implementation

### CLI Interface
```bash
stomper fix [OPTIONS] [FILES]

Options:
  # Quality tool flags (core tools)
  --ruff/--no-ruff              Enable/disable Ruff linting [default: True]
  --mypy/--no-mypy              Enable/disable MyPy type checking [default: True]
  --drill-sergeant/--no-drill-sergeant  Enable/disable Drill Sergeant [default: False]
  
  # Custom tools
  --extra-tools TEXT            Additional custom tools (comma-separated)
  
  # Processing options
  --file, -f PATH               Specific files to process
  --max-errors INT              Maximum errors to fix per iteration
  --error-type TEXT             Specific error types to fix (e.g., E501, F401)
  --interactive, -i             Interactive error type selection
  
  # AI agent options
  --agent TEXT                  AI agent to use [cursor-cli]
  --max-retries INT             Maximum retry attempts per file [3]
  
  # Execution options
  --dry-run                     Show what would be fixed without making changes
  --config, -c PATH             Path to configuration file
  --verbose, -v                 Verbose output
  --parallel                    Process files in parallel (experimental)
```

### Quality Tool Commands (Hybrid Approach)
```python
# Option B: Custom configuration first
if config.has_custom_command("ruff"):
    run_custom_command("ruff")

# Option A: Fall back to direct execution with package manager detection
def run_quality_tool(tool: str, args: List[str], config: StomperConfig = None):
    if config and config.has_custom_command(tool):
        cmd = config.get_custom_command(tool)
    else:
        project_manager = detect_project_manager()
        if project_manager == "uv":
            cmd = ["uv", "run", tool] + args
        elif project_manager == "poetry":
            cmd = ["poetry", "run", tool] + args
        else:
            cmd = [tool] + args
    
    return subprocess.run(cmd, capture_output=True, text=True)

# Examples:
# Ruff
run_quality_tool("ruff", ["check", "--output-format=json", "src/"])

# MyPy  
run_quality_tool("mypy", ["--show-error-codes", "--json-report", ".", "src/"])

# Drill Sergeant
run_quality_tool("drill-sergeant", ["--json", "tests/"])

# Pytest
run_quality_tool("pytest", ["--json-report", "tests/"])
```

### Error Mapping Structure
```
errors/
├── ruff/
│   ├── E501.md          # Line too long
│   ├── F401.md          # Imported but unused  
│   ├── F841.md          # Unused variable
│   └── ...
├── mypy/
│   ├── missing-return-type.md
│   ├── unused-ignore.md
│   └── ...
└── drill-sergeant/
    └── test-quality-issues.md
```

### AI Prompt Template
```
Fix the following issues in {file_path}:

{error_list}

Error-specific advice:
{error_advice}

Context:
- Total errors: {error_count}
- Auto-fixable errors: {auto_fixable_count}
- File type: {file_type}

Requirements:
1. Fix all listed issues
2. Maintain existing functionality
3. Follow project coding standards
4. Preserve test compatibility

Please provide the complete fixed file content.
```

## Workflow Algorithm

### Main Processing Loop
```python
def process_file(file_path: str) -> ProcessingResult:
    # 1. Collect errors for this file
    errors = collect_errors_for_file(file_path)
    
    # 2. Apply auto-fixes first
    auto_fixed = apply_auto_fixes(file_path, errors.auto_fixable)
    if auto_fixed:
        errors = collect_errors_for_file(file_path)  # Re-collect
    
    # 3. Generate AI prompt for remaining errors
    if errors.manual_fixable:
        prompt = build_ai_prompt(file_path, errors.manual_fixable)
        
        # 4. AI agent processing with retry logic
        for attempt in range(max_retries):
            fixed_content = call_ai_agent(prompt)
            if verify_fixes(file_path, fixed_content, errors):
                break
            else:
                prompt = update_prompt_with_feedback(prompt, attempt)
    
    # 5. Test validation
    if not run_tests():
        return ProcessingResult(success=False, reason="tests_failed")
    
    # 6. Git commit
    commit_changes(file_path, errors)
    
    return ProcessingResult(success=True)
```

### Error Collection
```python
def collect_errors_for_file(file_path: str) -> ErrorCollection:
    errors = ErrorCollection()
    
    # Run each quality tool
    for tool in enabled_tools:
        result = run_quality_tool(tool, file_path)
        parsed_errors = parse_tool_output(tool, result)
        errors.add_errors(tool, parsed_errors)
    
    # Categorize errors
    errors.categorize_by_fixability()
    return errors
```

### Fix Verification
```python
def verify_fixes(file_path: str, fixed_content: str, original_errors: List[Error]) -> bool:
    # Write fixed content to temporary file
    temp_file = write_temp_file(fixed_content)
    
    # Re-run quality tools on fixed file
    new_errors = collect_errors_for_file(temp_file)
    
    # Check if target errors are resolved
    resolved_errors = set(original_errors) - set(new_errors)
    return len(resolved_errors) == len(original_errors)
```

## Configuration

### Default Configuration
```toml
# Configuration file priority:
# 1. stomper.toml (dedicated config)
# 2. pyproject.toml [tool.stomper] (integrated config)
# 3. Default configuration (built-in)

[tool.stomper]
ai_agent = "cursor-cli"
max_retries = 3
parallel_files = 1
dry_run = false

# Tool configurations (hybrid approach)
[tool.stomper.tools.ruff]
command = "uv run ruff check --output-format=json src/"

[tool.stomper.tools.mypy]
command = "uv run mypy --show-error-codes --json-report . src/"

[tool.stomper.tools.drill-sergeant]
command = "uv run drill-sergeant --json tests/"

# Processing options
[tool.stomper.processing]
max_errors_per_iteration = 5
strategy = "batch_errors"  # or "one_error_type", "one_error_per_file"

[tool.stomper.ignores]
files = ["tests/**", "migrations/**", "*.pyc"]
errors = []

[tool.stomper.git]
branch_prefix = "stomper"
commit_style = "conventional"
auto_commit = true
```

### Environment Variables
```bash
STOMPER_AGENT_API_KEY=your_cursor_api_key
STOMPER_CONFIG_PATH=./stomper.toml
STOMPER_DRY_RUN=true
```

## Interactive Features

### Error Type Discovery and Selection
```python
# Interactive error selection with rich UI
stomper fix --interactive

# Displays table of available error types:
# ┌─────────────┬───────┬─────────┬───────┬─────────────────────────────┐
# │ Error Code  │ Count │ Tools   │ Files │ Sample Message              │
# ├─────────────┼───────┼─────────┼───────┼─────────────────────────────┤
# │ E501        │ 15    │ ruff    │ 8     │ Line too long (88 > 79)    │
# │ F401        │ 12    │ ruff    │ 5     │ Imported but unused        │
# │ missing-... │ 8     │ mypy    │ 6     │ Missing return type        │
# └─────────────┴───────┴─────────┴───────┴─────────────────────────────┘

# Selection options:
# 1. All - Fix all error types
# 2. Interactive - Select specific error types  
# 3. Auto - Let stomper choose the best strategy
```

### Dynamic Tool Flag Generation
```bash
# Auto-generate flags for custom tools
stomper fix --extra-tools black,isort,bandit

# This automatically creates:
# --black/--no-black
# --isort/--no-isort  
# --bandit/--no-bandit
```

## Error Handling

### Retry Logic
- **Quality tool failures**: Retry up to 3 times
- **AI agent failures**: Retry with updated prompts
- **Test failures**: Run tests multiple times for flaky tests
- **Git failures**: Rollback and retry

### Recovery Mechanisms
- **Git rollback**: Revert to last successful commit
- **Backup files**: Keep original file content
- **State persistence**: Resume from last successful file
- **Error logging**: Detailed logs for debugging

## Success Criteria

### MVP Success Metrics
- [ ] Successfully fixes 80% of auto-fixable errors
- [ ] Successfully fixes 60% of manual-fixable errors
- [ ] Maintains test suite integrity
- [ ] Creates proper git commits
- [ ] Handles tool failures gracefully
- [ ] Respects existing project configurations

### Quality Gates
- All tests must pass after fixes
- No new errors introduced
- Code functionality preserved
- Git history remains clean
- Performance impact minimal

## Future Enhancements

### Phase 2 Features
- Parallel file processing
- Multiple AI agent support
- Advanced error mapping strategies
- Learning from successful fixes
- Web dashboard for monitoring

### Phase 3 Features
- CI/CD integration
- Multi-language support
- Team collaboration features
- Advanced analytics
- Custom tool plugins
