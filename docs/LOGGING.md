# Logging in Stomper

## Overview

Stomper uses Python's standard logging module with Rich formatting for beautiful, colored console output! 🎨

## Logging Levels

The logging system has three levels you can control:

| Level | Flag | What You See |
|-------|------|-------------|
| **WARNING** | *(default)* | Only warnings and errors |
| **INFO** | `--verbose` or `-v` | General progress info + warnings/errors |
| **DEBUG** | `--debug` | Everything including detailed debug info |

## Usage Examples

### Basic Usage (Warnings Only)
```bash
# Only see warnings and errors
stomper fix --directory src/
```

### Verbose Mode (Recommended for Monitoring)
```bash
# See progress updates and what's happening
stomper fix --directory src/ --verbose

# Short form
stomper fix -d src/ -v
```

### Debug Mode (for Troubleshooting)
```bash
# See everything including internal details
stomper fix --directory src/ --debug
```

### Logging to File
```bash
# Log to file AND console
stomper fix --directory src/ --debug --log-file stomper.log

# Or combine with verbose
stomper fix -d src/ -v --log-file fixes.log
```

## What You'll See

### WARNING Level (Default)
```
⚠️ Running on Windows without WSL - cursor-agent may not be available
❌ Failed to fix error in file.py
```

### INFO Level (--verbose)
```
🪟 Running on Windows - cursor-agent will be executed via WSL
✅ Cursor CLI available and ready
📝 Generating prompt for test1.py (attempt 1)
🔍 Verifying fixes for test1.py
```

### DEBUG Level (--debug)
```
🔧 Debug logging enabled (level: DEBUG)
ErrorMapper initialized with storage: E:\project\.stomper\learning_data.json
Executing command: wsl --cd /mnt/e/project -- cursor-agent --version
Working directory: E:\project
[STDOUT] {"type": "event", "data": "..."}
[JSON] {"type": "result", "duration_ms": 1234}
```

## Rich Logging Features

Stomper's logging includes:

- ✨ **Rich Colors** - Different colors for different log levels
- 📅 **Timestamps** - See exactly when things happened
- 🎯 **Emoji Icons** - Visual indicators for different operations
- 🖼️ **Beautiful Formatting** - Tables, panels, and aligned text
- 🔍 **Rich Tracebacks** - Detailed, colorful error traces when things go wrong

## Programmatic Logging

If you're using Stomper as a library:

```python
from stomper.workflow.logging import setup_workflow_logging

# Setup logging
setup_workflow_logging(
    level="DEBUG",  # or "INFO", "WARNING", "ERROR"
    log_file=Path("my-log.log")  # Optional
)

# Then use standard logging
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

## Log File Format

When using `--log-file`, the file contains standard formatted logs:

```
2025-10-09 15:30:45 - stomper.ai.cursor_client - INFO - Cursor CLI available and ready
2025-10-09 15:30:46 - stomper.ai.mapper - DEBUG - ErrorMapper initialized with storage: .stomper/learning_data.json
2025-10-09 15:30:47 - stomper.workflow.orchestrator - INFO - Starting workflow execution
```

## Debugging Tips

### 1. Start with Verbose
```bash
stomper fix -d src/ -v
```

### 2. Add Debug if Issues
```bash
stomper fix -d src/ --debug
```

### 3. Save Debug Output
```bash
stomper fix -d src/ --debug --log-file debug.log
```

### 4. Check Specific Components

The loggers are organized by module:

- `stomper.ai.cursor_client` - Cursor agent interaction
- `stomper.ai.mapper` - Error pattern learning
- `stomper.ai.sandbox_manager` - Sandbox operations
- `stomper.workflow.orchestrator` - Workflow execution
- `stomper.quality.*` - Quality tool operations

## Environment Variables

You can also control logging via environment:

```bash
# Set log level
export STOMPER_LOG_LEVEL=DEBUG

# Then run normally
stomper fix -d src/
```

*(Note: CLI flags override environment variables)*

## Common Issues

### Not Seeing Logs?

1. Make sure you're using `--verbose` or `--debug`
2. Check that the command is actually running
3. Try `--debug --log-file test.log` to see if file logging works

### Too Much Output?

1. Remove `--debug` flag
2. Use default (WARNING only) or `--verbose` (INFO)
3. Use `--log-file` to send details to file instead

### Emoji Not Showing?

On Windows:
- Use Windows Terminal (not cmd.exe)
- Ensure UTF-8 encoding is enabled
- Stomper auto-configures UTF-8 on Windows

## Quick Reference

```bash
# Default (minimal output)
stomper fix -d src/

# Show progress
stomper fix -d src/ --verbose

# Full debug
stomper fix -d src/ --debug

# Save to file
stomper fix -d src/ -v --log-file run.log

# Debug to file only
stomper fix -d src/ --debug --log-file debug.log
```

Enjoy your beautifully logged Stomper experience! 🎉✨

