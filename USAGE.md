# Stomper Usage Guide

## 🚀 Quick Start

```bash
# Install
pip install stomper

# Basic usage - fix all quality issues in your project
stomper

# Dry run to see what would be fixed
stomper --dry-run
```

## 📁 File Selection Options

### Single File
```bash
stomper --file src/my_module.py
stomper -f src/my_module.py
```

### Multiple Files
```bash
stomper --files src/file1.py,src/file2.py,tests/test_file.py
```

### Directory
```bash
stomper --directory src/
stomper -d src/
```

### Pattern Matching
```bash
stomper --pattern "src/**/*.py"
stomper --pattern "tests/test_*.py"
```

### Git Integration
```bash
# Fix only changed (unstaged) files
stomper --git-changed

# Fix only staged files
stomper --git-staged

# Fix files changed since main branch
stomper --git-diff main

# Fix files changed since develop branch
stomper --git-diff develop
```

## 🔧 Quality Tool Options

### Enable/Disable Tools
```bash
# Only run Ruff
stomper --mypy=false

# Only run MyPy
stomper --ruff=false

# Enable Drill Sergeant
stomper --drill-sergeant
```

### Error Filtering
```bash
# Fix only specific error types
stomper --error-type E501,F401

# Ignore specific error codes
stomper --ignore E501,F401

# Limit number of errors to fix
stomper --max-errors 50
```

## 🎯 Advanced Options

### File Filtering
```bash
# Exclude patterns
stomper --exclude "**/test_*.py,**/migrations/**"

# Limit number of files
stomper --max-files 100
```

### Output Control
```bash
# Verbose output
stomper --verbose

# Show version
stomper --version
```

## 🔄 Workflow Examples

### Pre-commit Workflow
```bash
# Stage your changes
git add src/my_changes.py

# Fix only staged files
stomper --git-staged
```

### Feature Branch Development
```bash
# Fix all changes in your feature branch vs main
stomper --git-diff main

# Fix only what you've changed locally
stomper --git-changed
```

### CI/CD Pipeline
```bash
# Fix files changed in this PR
stomper --git-diff $BASE_BRANCH --dry-run
```

### Development Workflow
```bash
# Quick fix for current directory
stomper --directory src/

# Fix specific files you're working on
stomper --files src/module1.py,src/module2.py

# Fix with error filtering
stomper --error-type E501,F401 --ignore F841
```

## ⚙️ Configuration

Create a `pyproject.toml` file in your project root:

```toml
[tool.stomper]
quality_tools = ["ruff", "mypy"]
ai_agent = "cursor-cli"
max_retries = 3
parallel_files = 1

[tool.stomper.files]
include = ["src/**/*.py", "tests/**/*.py"]
exclude = ["**/migrations/**", "**/legacy/**"]
max_files_per_run = 100
parallel_processing = true
```

## 🚨 Error Handling

### Not in Git Repository
```bash
$ stomper --git-changed
Git Error: Not in a git repository
Falling back to processing all files in project
```

### No Files Found
```bash
$ stomper --git-changed --dry-run
No git-tracked files found to process
```

### Tool Not Available
```bash
$ stomper --drill-sergeant
Tools not available: drill-sergeant
```

## 💡 Pro Tips

1. **Always use `--dry-run` first** to see what will be processed
2. **Stage files before using `--git-staged`** for pre-commit workflows
3. **Use `--git-diff main`** for feature branch development
4. **Combine with `--verbose`** for detailed output
5. **Use `--max-files`** to limit processing on large changesets
6. **Use `--max-errors`** to prevent overwhelming fixes

## 🔍 Understanding Output

### Configuration Summary
- Shows enabled tools, dry run status, and settings
- Displays file discovery results with counts and sizes

### Quality Assessment
- Lists issues found by each tool
- Shows status (Ready to Fix vs Dry Run)

### File Discovery
- Shows target (file/directory/pattern/git)
- Displays file counts and sizes
- Lists directories processed

### Git Integration
- Shows git status summary
- Displays which files are staged/changed
- Indicates branch comparisons
