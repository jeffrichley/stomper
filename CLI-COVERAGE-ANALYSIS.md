# CLI Configuration Coverage Analysis

## ❌ Missing Configuration Parameters in CLI

Your CLI `fix` command is **missing several important workflow configuration parameters**!

---

## 📊 Coverage Summary

### ✅ **Exposed in CLI (14 parameters):**

#### Quality Tools:
- ✅ `--ruff/--no-ruff`
- ✅ `--mypy/--no-mypy`
- ✅ `--drill-sergeant/--no-drill-sergeant`

#### File Selection:
- ✅ `--file` / `-f`
- ✅ `--files`
- ✅ `--directory` / `-d`
- ✅ `--pattern`
- ✅ `--git-changed`
- ✅ `--git-staged`
- ✅ `--git-diff`

#### Error Filtering:
- ✅ `--error-type`
- ✅ `--ignore`
- ✅ `--exclude`
- ✅ `--max-errors`

#### Processing:
- ✅ `--max-files`
- ✅ `--dry-run`
- ✅ `--verbose` / `-v`

---

### ❌ **MISSING from CLI (10+ parameters):**

#### Workflow Configuration:
- ❌ `--use-sandbox` / `--no-use-sandbox` (WorkflowConfig.use_sandbox)
- ❌ `--run-tests` / `--no-run-tests` (WorkflowConfig.run_tests)
- ❌ `--max-retries` (WorkflowConfig.max_retries)
- ❌ `--processing-strategy` (WorkflowConfig.processing_strategy)
- ❌ `--agent-name` (WorkflowConfig.agent_name)

#### Per-File Worktree Architecture (NEW):
- ❌ `--test-validation` (WorkflowConfig.test_validation)
  - Options: `full`, `quick`, `final`, `none`
- ❌ `--files-per-worktree` (WorkflowConfig.files_per_worktree)
- ❌ `--continue-on-error` / `--no-continue-on-error` (WorkflowConfig.continue_on_error)

#### **🚨 CRITICAL - Parallel Processing (Phase 2):**
- ❌ `--max-parallel-files` (WorkflowConfig.max_parallel_files)
  - **This is your new parallel processing feature!**
  - Default: 4
  - Range: 1-32

#### Files Configuration:
- ❌ `--include` (FilesConfig.include patterns)
- ❌ `--max-files-per-run` (FilesConfig.max_files_per_run)
- ❌ `--parallel-processing` / `--no-parallel-processing` (FilesConfig.parallel_processing)

#### Git Configuration:
- ❌ `--branch-prefix` (GitConfig.branch_prefix)
- ❌ `--commit-style` (GitConfig.commit_style)

---

## 🔥 **Most Important Missing Parameters**

### 1. **`--max-parallel-files` (CRITICAL!)**
**You just implemented Phase 2 parallel processing but can't control it from CLI!**

```bash
# Currently NOT possible:
stomper fix src/ --max-parallel-files 8

# Users can only use default (4) or edit config file
```

### 2. **`--use-sandbox` / `--no-use-sandbox`**
**Critical for controlling worktree vs direct mode:**

```bash
# NOT possible:
stomper fix src/ --no-use-sandbox  # Direct mode (simpler)
stomper fix src/ --use-sandbox     # Worktree mode (safer)
```

### 3. **`--run-tests` / `--no-run-tests`**
**Control test validation:**

```bash
# NOT possible:
stomper fix src/ --no-run-tests  # Skip tests for speed
stomper fix src/ --run-tests     # Validate with tests
```

### 4. **`--test-validation`**
**Control test validation strategy:**

```bash
# NOT possible:
stomper fix src/ --test-validation full   # All tests per file
stomper fix src/ --test-validation quick  # Affected tests only
stomper fix src/ --test-validation final  # Once at end
stomper fix src/ --test-validation none   # Skip tests
```

### 5. **`--continue-on-error`**
**Control error handling:**

```bash
# NOT possible:
stomper fix src/ --continue-on-error     # Keep going
stomper fix src/ --no-continue-on-error  # Stop on first error
```

---

## 📝 **Recommended CLI Additions**

### **High Priority (Must Add):**

```python
@app.command()
def fix(
    # ... existing parameters ...
    
    # WORKFLOW CONFIGURATION (HIGH PRIORITY)
    use_sandbox: bool = typer.Option(
        True, "--use-sandbox/--no-use-sandbox", 
        help="Use git worktree sandbox for isolated execution"
    ),
    run_tests: bool = typer.Option(
        True, "--run-tests/--no-run-tests",
        help="Run tests after fixes to validate"
    ),
    max_parallel_files: int = typer.Option(
        4, "--max-parallel-files",
        help="Maximum files to process in parallel (1=sequential, 4=default, 32=max)"
    ),
    test_validation: str = typer.Option(
        "full", "--test-validation",
        help="Test validation mode: full, quick, final, or none"
    ),
    continue_on_error: bool = typer.Option(
        True, "--continue-on-error/--no-continue-on-error",
        help="Continue processing other files after a file fails"
    ),
    
    # ... rest of function ...
) -> None:
    """Fix code quality issues in your codebase."""
```

### **Medium Priority:**

```python
    max_retries: int = typer.Option(
        3, "--max-retries",
        help="Maximum retry attempts per file"
    ),
    processing_strategy: str = typer.Option(
        "batch_errors", "--processing-strategy",
        help="Processing strategy: batch_errors, one_error_type, all_errors"
    ),
    agent_name: str = typer.Option(
        "cursor-cli", "--agent-name",
        help="AI agent to use for fixing"
    ),
```

### **Low Priority (Advanced):**

```python
    files_per_worktree: int = typer.Option(
        1, "--files-per-worktree",
        help="Files per worktree (1=per-file isolation)"
    ),
    include_patterns: str = typer.Option(
        None, "--include",
        help="Include patterns for file discovery (comma-separated)"
    ),
    branch_prefix: str = typer.Option(
        "stomper", "--branch-prefix",
        help="Prefix for auto-generated branches"
    ),
```

---

## 🛠️ **Quick Fix Implementation**

### **Add to `fix()` function signature:**

```python
@app.command()
def fix(
    # ... existing parameters ...
    
    # ADD THESE:
    use_sandbox: bool = typer.Option(True, "--use-sandbox/--no-use-sandbox", help="Use git worktree sandbox"),
    run_tests: bool = typer.Option(True, "--run-tests/--no-run-tests", help="Run tests after fixes"),
    max_parallel_files: int = typer.Option(4, "--max-parallel-files", help="Max parallel files (1-32)"),
    test_validation: str = typer.Option("full", "--test-validation", help="full|quick|final|none"),
    continue_on_error: bool = typer.Option(True, "--continue-on-error/--no-continue-on-error", help="Continue on error"),
    max_retries: int = typer.Option(3, "--max-retries", help="Maximum retry attempts"),
) -> None:
```

### **Add to `ConfigOverride` creation (around line 395):**

```python
cli_overrides = ConfigOverride(
    ruff=ruff,
    mypy=mypy,
    drill_sergeant=drill_sergeant,
    file=file,
    files=[Path(f.strip()) for f in files.split(",")] if files else None,
    directory=directory,
    error_type=error_type,
    ignore=[i.strip() for i in ignore.split(",")] if ignore else None,
    max_errors=max_errors,
    dry_run=dry_run,
    verbose=verbose,
    
    # ADD THESE:
    use_sandbox=use_sandbox,
    run_tests=run_tests,
    max_parallel_files=max_parallel_files,
    test_validation=test_validation,
    continue_on_error=continue_on_error,
    max_retries=max_retries,
)
```

---

## 🎯 **Impact Analysis**

### **Current Situation:**
- Users **cannot** control parallel processing from CLI
- Users **cannot** disable sandbox/tests for faster debugging
- Users **must** edit `stomper.toml` for any workflow changes
- Your Phase 2 parallel feature is **hidden**!

### **After Adding Parameters:**
- ✅ Full control over parallel processing
- ✅ Easy debugging (disable sandbox/tests)
- ✅ Power users can customize everything
- ✅ Your Phase 2 feature is **discoverable**!

---

## 📈 **Usage Examples (After Fix)**

### **Debug Mode (Fast):**
```bash
stomper fix src/ \
  --no-use-sandbox \
  --no-run-tests \
  --max-parallel-files 1
```

### **Production Mode (Safe):**
```bash
stomper fix src/ \
  --use-sandbox \
  --run-tests \
  --test-validation full \
  --max-parallel-files 4
```

### **Speed Mode (Parallel):**
```bash
stomper fix src/ \
  --use-sandbox \
  --no-run-tests \
  --max-parallel-files 8
```

### **CI/CD Mode:**
```bash
stomper fix src/ \
  --use-sandbox \
  --test-validation final \
  --max-parallel-files 16 \
  --continue-on-error
```

---

## ✅ **Action Items**

1. **Immediate:** Add `--max-parallel-files` to expose Phase 2 feature
2. **High Priority:** Add `--use-sandbox` and `--run-tests` for debugging
3. **Medium Priority:** Add `--test-validation` and `--continue-on-error`
4. **Low Priority:** Add remaining workflow parameters

---

## 🎓 **Summary**

**Current CLI Coverage: ~58% (14/24 parameters)**

**Missing Critical Parameters:**
- ❌ `--max-parallel-files` (Your Phase 2 feature!)
- ❌ `--use-sandbox`
- ❌ `--run-tests`
- ❌ `--test-validation`
- ❌ `--continue-on-error`

**Recommendation:** Add at least the 5 critical parameters above to make your parallel processing feature usable and discoverable! 🚀

