# Stomper Architecture Design

## Core Workflow

```
1. Quality Assessment → 2. Auto-Fix → 3. AI Agent Fix → 4. Test Validation → 5. Git Commit
```

## Project Structure

```
stomper/
├── src/stomper/
│   ├── __init__.py
│   ├── cli.py                    # Main CLI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Main workflow orchestration
│   │   └── state.py              # Processing state management
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── base.py               # Base quality tool interface
│   │   ├── ruff.py               # Ruff integration
│   │   ├── mypy.py               # MyPy integration
│   │   ├── drill_sergeant.py     # Drill Sergeant integration
│   │   └── pytest.py             # Pytest integration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py               # Base agent interface
│   │   ├── cursor_cli.py         # Cursor CLI integration
│   │   └── prompt_builder.py     # Error-to-prompt conversion
│   ├── git/
│   │   ├── __init__.py
│   │   ├── manager.py            # Git operations
│   │   ├── branch.py             # Branch management
│   │   └── commit.py             # Commit generation
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── collector.py          # Error collection and parsing
│   │   ├── mapper.py             # Error code to advice mapping
│   │   └── resolver.py           # Error resolution tracking
│   └── config/
│       ├── __init__.py
│       ├── loader.py             # Configuration loading
│       └── validator.py          # Configuration validation
├── errors/                       # Error mapping files
│   ├── ruff/
│   ├── mypy/
│   └── drill-sergeant/
├── tests/
│   ├── unit/
│   └── integration/
└── pyproject.toml
```

## Quality Tool Integration

### Direct Tool Execution
- **Ruff**: `ruff check --output-format=json src/`
- **MyPy**: `mypy --show-error-codes --json-report . src/`
- **Drill Sergeant**: `drill-sergeant --json tests/`
- **Pytest**: `pytest --json-report tests/`

### Configuration Discovery
Tools automatically discover project configs:
- `pyproject.toml` → `[tool.ruff]`, `[tool.mypy]`
- `ruff.toml`, `mypy.ini`, `setup.cfg`
- Respect existing user configurations

## Error Mapping System

### Simple File-Based Structure
```
errors/ruff/E501.md:
# Line too long (E501)

Split long lines using parentheses or backslashes.

## Examples:
- Use parentheses for function calls
- Extract complex expressions to variables
- Use string concatenation for long strings
```

### Error Collection Flow
1. Run quality tools with JSON output
2. Parse error results into structured data
3. Group errors by file and type
4. Load advice from error mapping files
5. Generate AI prompts with context

## AI Agent Integration

### Cursor CLI Integration
- Headless mode: `cursor --headless --file {file} --prompt "{prompt}"`
- File-specific processing
- Structured prompt generation
- Response parsing and validation

### Prompt Structure
```
Fix the following issues in {file}:

{error_descriptions}

Error-specific advice:
{error_advice}

Context:
- File: {file}
- Error count: {count}
- Auto-fixable: {auto_fixable_errors}

Please fix these issues while maintaining:
- Code functionality
- Test compatibility
- Style consistency
```

## Git Integration

### Branch Strategy
- Session branch: `stomper/auto-fixes-{timestamp}`
- Atomic commits per file
- Conventional commit messages
- Rollback capabilities

### Commit Messages
```
fix(quality): resolve linting issues in auth.py

- E501: Split long lines using parentheses
- F401: Remove unused imports
- F841: Remove unused variables

Fixed by: stomper v0.1.0
```

## Configuration System

### CLI Options
```bash
stomper fix [OPTIONS]

Options:
  --tools TEXT         Quality tools to run [ruff, mypy, drill-sergeant]
  --files PATH         Specific files to process
  --ignore TEXT        Error codes to ignore
  --agent TEXT         AI agent to use [cursor-cli]
  --max-retries INT    Maximum retry attempts
  --dry-run           Show what would be fixed
```

### Configuration File
```toml
[tool.stomper]
quality_tools = ["ruff", "mypy"]
ai_agent = "cursor-cli"
max_retries = 3
parallel_files = 1

[tool.stomper.ignores]
files = ["tests/**", "migrations/**"]
errors = ["E501", "F401"]

[tool.stomper.git]
branch_prefix = "stomper"
commit_style = "conventional"
```
