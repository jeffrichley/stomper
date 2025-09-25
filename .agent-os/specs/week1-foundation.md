# Week 1 Foundation - Stomper CLI Framework

## Overview
Establish the foundational CLI framework, configuration system, and quality tool integration for the Stomper automated code quality fixing tool.

## Progress Status 🚀

### ✅ COMPLETED
- **Task 1: CLI Framework Setup** - Fully implemented with all acceptance criteria met
- **CLI Entry Points** - `stomper` and `stomp` commands working perfectly
- **Rich Terminal Output** - Beautiful formatting with progress indicators
- **Comprehensive Testing** - 13 tests passing with 0 warnings
- **Code Quality** - Type hints, clean code, proper test organization
- **Task 2: Configuration System** - Fully implemented with comprehensive testing
- **Configuration Models** - Complete Pydantic models with validation
- **Configuration Loader** - TOML loading, environment variables, CLI overrides
- **Configuration Validator** - Full validation with clear error messages

### ✅ COMPLETED
- **Task 3: Quality Tool Integration** - Core tools (Ruff, MyPy) fully implemented
- **Quality Tool Infrastructure** - Base classes, managers, and integrations
- **Error Collection & Parsing** - JSON parsing and structured error models
- **CLI Integration** - Quality tools working in the main CLI
- **Task 4: Error Collection and Parsing** - Enhanced error handling and filtering

### 🔄 IN PROGRESS
- **Week 2: AI Agent Integration** - Next major milestone

### ⏳ PENDING (End of Plan)
- **Drill Sergeant Integration** - Test quality tool (low priority)
- **Pytest Integration** - Test runner integration (low priority)

## Technical Requirements

### 1. CLI Framework Setup
**Goal**: Create a modern, type-safe CLI interface using Typer

**Acceptance Criteria**:
- [x] Main CLI entry point with `stomper` command
- [x] `stomper fix` subcommand with proper argument parsing
- [x] Support for quality tool flags (`--ruff`, `--mypy`, `--drill-sergeant`)
- [x] File selection options (`--file`, `--files`)
- [x] Error filtering options (`--error-type`, `--ignore`)
- [x] Processing options (`--max-errors`, `--dry-run`)
- [x] Rich terminal output with progress indicators
- [x] Comprehensive help documentation

**Technical Implementation**:
```python
# CLI Structure
stomper/
├── cli.py                    # Main CLI entry point
├── commands/
│   ├── __init__.py
│   └── fix.py               # Fix command implementation
└── models/
    ├── __init__.py
    └── cli.py               # CLI data models
```

**Dependencies**:
- `typer>=0.9.0` - Modern CLI framework
- `rich>=13.0.0` - Beautiful terminal output
- `pydantic>=2.0.0` - Data validation

### 2. Configuration System
**Goal**: TOML-based configuration with pyproject.toml integration

**Acceptance Criteria**:
- [x] Load configuration from `pyproject.toml` `[tool.stomper]` section
- [x] Support for default configuration values
- [x] Configuration validation with clear error messages
- [x] CLI argument override capability
- [x] Configuration discovery for quality tools
- [x] Environment variable support

**Configuration Schema**:
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

**Technical Implementation**:
```python
# Configuration Structure
stomper/
├── config/
│   ├── __init__.py
│   ├── loader.py           # Configuration loading
│   ├── validator.py        # Configuration validation
│   └── models.py           # Configuration data models
```

### 3. Quality Tool Integration
**Goal**: Direct execution of quality tools with JSON output parsing

**Acceptance Criteria**:
- [x] Ruff integration with `ruff check --output-format=json`
- [x] MyPy integration with `mypy --show-error-codes --output json`
- [ ] Drill Sergeant integration with `drill-sergeant --json` (moved to end of plan)
- [ ] Pytest integration with `pytest --json-report` (moved to end of plan)
- [x] Tool configuration discovery from pyproject.toml
- [x] Error output parsing into structured data
- [x] Tool execution error handling

**Quality Tool Commands**:
```bash
# Ruff
ruff check --output-format=json src/

# MyPy  
mypy --show-error-codes --json-report . src/

# Drill Sergeant
drill-sergeant --json tests/

# Pytest
pytest --json-report tests/
```

**Technical Implementation**:
```python
# Quality Tools Structure
stomper/
├── quality/
│   ├── __init__.py
│   ├── base.py             # Base quality tool interface
│   ├── ruff.py             # Ruff integration
│   ├── mypy.py             # MyPy integration
│   ├── drill_sergeant.py   # Drill Sergeant integration
│   └── pytest.py           # Pytest integration
```

### 4. Error Collection and Parsing
**Goal**: Structured error data collection and organization

**Acceptance Criteria**:
- [ ] Parse JSON output from all quality tools
- [ ] Group errors by file and error type
- [ ] Error data models with validation
- [ ] Error filtering and selection
- [ ] Error statistics and reporting
- [ ] Error persistence for tracking

**Error Data Model**:
```python
@dataclass
class QualityError:
    tool: str
    file: Path
    line: int
    column: int
    code: str
    message: str
    severity: str
    auto_fixable: bool
```

**Technical Implementation**:
```python
# Error Collection Structure
stomper/
├── errors/
│   ├── __init__.py
│   ├── collector.py        # Error collection and parsing
│   ├── models.py           # Error data models
│   └── filter.py           # Error filtering logic
```

## Implementation Tasks

### Task 1: CLI Framework Setup ✅ COMPLETED
1. **Setup project dependencies** - Add typer, rich, pydantic to pyproject.toml ✅
2. **Create CLI entry point** - Implement main `stomper` command ✅
3. **Implement fix command** - Create `stomper fix` subcommand ✅
4. **Add argument parsing** - Support all required CLI options ✅
5. **Add rich output** - Beautiful terminal interface with progress ✅
6. **Write CLI tests** - Unit tests for CLI functionality ✅

### Task 2: Configuration System
1. **Create configuration models** - Pydantic models for config validation
2. **Implement config loader** - Load from pyproject.toml and defaults
3. **Add configuration validation** - Validate config with clear errors
4. **Implement CLI overrides** - Allow CLI args to override config
5. **Add environment support** - Support environment variables
6. **Write config tests** - Unit tests for configuration system

### Task 3: Quality Tool Integration
1. **Create base tool interface** - Abstract base class for quality tools
2. **Implement Ruff integration** - Execute ruff and parse JSON output
3. **Implement MyPy integration** - Execute mypy and parse JSON output
4. **Implement Drill Sergeant integration** - Execute drill-sergeant and parse JSON
5. **Implement Pytest integration** - Execute pytest and parse JSON output
6. **Add tool configuration discovery** - Auto-detect tool configs
7. **Write tool tests** - Unit tests for each quality tool

### Task 4: Error Collection and Parsing
1. **Create error data models** - Pydantic models for error data
2. **Implement error collector** - Parse JSON output from tools
3. **Add error grouping** - Group errors by file and type
4. **Implement error filtering** - Filter errors by type, file, etc.
5. **Add error statistics** - Count and categorize errors
6. **Write error tests** - Unit tests for error collection

## Testing Strategy

### Unit Tests
- CLI command parsing and validation
- Configuration loading and validation
- Quality tool execution and parsing
- Error collection and filtering

### Integration Tests
- End-to-end CLI workflow
- Configuration file integration
- Quality tool execution with real projects
- Error collection from actual tool outputs

### Test Coverage
- Minimum 80% code coverage
- All public APIs tested
- Error handling scenarios covered
- Configuration edge cases tested

## Success Criteria

### Functional Requirements
- [x] CLI accepts all required arguments and options
- [ ] Configuration loads correctly from pyproject.toml
- [ ] All quality tools execute and return structured data
- [ ] Errors are collected and organized properly
- [x] Rich terminal output provides clear feedback

### Quality Requirements
- [x] All code follows project style guidelines
- [x] Comprehensive test coverage (80%+)
- [x] Clear error messages and documentation
- [x] Type hints throughout codebase
- [x] No linting errors or type errors

### Performance Requirements
- [x] CLI startup time < 1 second
- [ ] Quality tool execution time reasonable
- [ ] Memory usage optimized for large projects
- [ ] Error collection efficient for many files

## Dependencies

### Core Dependencies
```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0", 
    "pydantic>=2.0.0",
    "click>=8.0.0",
    "toml>=0.10.0",
]
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "black>=23.0.0",
]
```

## Timeline

**Estimated Duration**: 1 week (5 days)

**Day 1**: CLI Framework Setup
**Day 2**: Configuration System  
**Day 3**: Quality Tool Integration
**Day 4**: Error Collection and Parsing
**Day 5**: Testing, Documentation, and Integration

## Next Steps

After completing Week 1 Foundation:
1. **Week 2**: AI Agent Integration
2. **Week 3**: Testing & Validation
3. **Week 4**: Git Integration

This spec provides the foundation for implementing the core CLI framework and quality tool integration that will enable the automated fixing workflow in subsequent weeks.
