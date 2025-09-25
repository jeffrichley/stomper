---
alwaysApply: true
---

# Stomper - Automated Code Quality Fixing Tool

## Agent OS Documentation

### Product Context
- **Mission & Vision:** .agent-os/product/mission.md
- **Technical Architecture:** .agent-os/product/tech-stack.md
- **Development Roadmap:** .agent-os/product/roadmap.md
- **Decision History:** .agent-os/product/decisions.md

### Development Standards
- **Code Style:** ~/.agent-os/standards/code-style.md
- **Best Practices:** ~/.agent-os/standards/best-practices.md

### Project Management
- **Active Specs:** .agent-os/specs/
- **Spec Planning:** Use `~/.agent-os/instructions/create-spec.md`
- **Tasks Execution:** Use `~/.agent-os/instructions/execute-tasks.md`

## Workflow Instructions

When asked to work on this codebase:

1. **First**, check .agent-os/product/roadmap.md for current priorities
2. **Then**, follow the appropriate instruction file:
   - For new features: ~/.agent-os/instructions/create-spec.md
   - For tasks execution: ~/.agent-os/instructions/execute-tasks.md
3. **Always**, adhere to the standards in the files listed above

## Important Notes

- Product-specific files in `.agent-os/product/` override any global standards
- User's specific instructions override (or amend) instructions found in `.agent-os/specs/...`
- Always adhere to established patterns, code style, and best practices documented above.

## Project Overview

Stomper is an automated code quality fixing tool that systematically resolves linting errors, type errors, and test failures using AI agents while maintaining code integrity. The tool targets Python developers who want to eliminate the tedious manual process of fixing code quality issues.

### Key Features
- Automated fixing of linting errors (Ruff, MyPy, Drill Sergeant)
- AI agent integration via cursor-cli headless mode
- LangGraph state machine for complex workflow orchestration
- Interactive error type selection with rich UI
- Dynamic tool flag generation for custom tools
- Hybrid tool execution (custom config + auto-detection)
- Git integration with atomic commits and rollback support
- Comprehensive testing and validation

### Technical Stack
- **Python 3.13+** with Typer CLI framework
- **LangChain + LangGraph** for AI agent orchestration
- **Rich** for beautiful terminal output
- **Pydantic** for configuration validation
- **UV/Poetry/pip** package manager support
- **GitHub Actions** for CI/CD

### Current Status
The project is currently in the planning phase with comprehensive documentation completed. Development is ready to begin with Phase 1: Core MVP features.