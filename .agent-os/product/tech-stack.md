# Stomper Technical Architecture

## Core Technology Stack

### Runtime & CLI
- **Python 3.13+**: Primary language for CLI tool
- **Typer**: Modern command-line interface framework with type hints
- **Rich**: Beautiful terminal output and progress tracking
- **Pydantic**: Configuration validation and data models

### AI Agent Integration
- **Cursor CLI**: Primary AI agent via headless mode
- **LangChain**: Tool integration and agent orchestration
- **LangGraph**: State machine for complex workflows
- **OpenAI API**: Multi-provider AI support
- **Anthropic Claude**: Alternative agent support

### Quality Tools Integration
- **Ruff**: Python linting and formatting
- **MyPy**: Static type checking
- **Drill-Sergeant**: Custom test quality analysis
- **Pytest**: Test execution and validation
- **Black**: Code formatting (future)
- **isort**: Import sorting (future)
- **Bandit**: Security linting (future)

### Git & Version Control
- **GitPython**: Git operations and branch management
- **Git Worktrees**: Parallel processing support (future)
- **Conventional Commits**: Standardized commit messages

### Configuration & Data
- **TOML**: Configuration file format
- **JSON**: Error mapping and agent communication
- **YAML**: Advanced configuration options (future)

### Testing & Quality
- **Pytest**: Unit and integration testing
- **Coverage.py**: Code coverage analysis
- **GitHub Actions**: CI/CD matrix testing
- **UV**: Python package and environment management

## Architecture Patterns

### Plugin Architecture
- Modular quality tool integration
- Extensible AI agent support
- Configurable error mapping strategies

### State Management
- File-level processing state
- Error tracking and resolution history
- Rollback and recovery mechanisms

### Async Processing
- Sequential processing (MVP)
- Parallel processing (future)
- Agent coordination via MCP servers (future)
