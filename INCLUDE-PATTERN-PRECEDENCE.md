# Include Pattern Precedence System

## 🎯 The Problem (Fixed!)

**Before:** When using `--directory test_errors/`, no files were found because the hardcoded default patterns `["src/**/*.py", "tests/**/*.py"]` didn't match.

**Solution:** Added `--include` CLI parameter with smart precedence based on context.

---

## ✅ New Precedence System

### **Priority Order (Highest to Lowest):**

1. **CLI `--include`** - User explicitly specifies patterns
2. **Context-based default** - Sensible default based on what user is doing
3. **Config file** - Default from `stomper.toml` or `FilesConfig`

---

## 📊 How It Works

### **Scenario 1: User Specifies `--include`** (Highest Priority)
```bash
stomper fix --directory test_errors/ --include "**/*.py,**/*.pyi"
```
**Result:** Uses `["**/*.py", "**/*.pyi"]` ✅

**Reasoning:** User knows exactly what they want - honor their choice!

---

### **Scenario 2: User Specifies `--directory` (Context-Based Default)**
```bash
stomper fix --directory test_errors/
```
**Result:** Uses `["**/*.py"]` in `test_errors/` ✅

**Reasoning:** When targeting a specific directory, user expects ALL Python files in that directory, not just `src/` and `tests/` subdirectories.

**Don't Surprise Me:** ✅ This is what users expect!

---

### **Scenario 3: No Directory, No Include (Config Default)**
```bash
stomper fix
```
**Result:** Uses config defaults `["src/**/*.py", "tests/**/*.py"]` ✅

**Reasoning:** Scanning whole project - use config defaults designed for project structure.

**Don't Surprise Me:** ✅ Respects project configuration!

---

## 🔍 Example Use Cases

### **Use Case 1: Test on Specific Directory**
```bash
# Auto-detects all .py files in test_errors/
stomper fix --directory test_errors/ --ruff --dry-run
```

### **Use Case 2: Custom Patterns**
```bash
# Only type stub files
stomper fix --directory src/ --include "**/*.pyi"

# Multiple patterns
stomper fix --directory lib/ --include "**/*.py,**/*.pyx"
```

### **Use Case 3: Override Defaults**
```bash
# Include ALL Python files in project, not just src/ and tests/
stomper fix --include "**/*.py"

# Include specific subdirectories
stomper fix --include "app/**/*.py,scripts/**/*.py"
```

### **Use Case 4: With Exclude**
```bash
# All Python files except migrations
stomper fix --directory src/ --exclude "**/migrations/**"

# Custom include + exclude
stomper fix --include "**/*.py" --exclude "**/test_*.py,**/migrations/**"
```

---

## 💡 Implementation Details

### **Code Location:** `src/stomper/cli.py`

```python
# Parse include patterns with proper precedence
include_patterns = None
if include:
    # CLI explicitly specified - highest priority
    include_patterns = [p.strip() for p in include.split(",") if p.strip()]
elif directory:
    # User specified a directory - use sensible default for that directory
    include_patterns = ["**/*.py"]
else:
    # Use config defaults (typically ["src/**/*.py", "tests/**/*.py"])
    include_patterns = config_files.include
```

### **Pattern Format:**
- Comma-separated glob patterns
- Relative to the target path
- Standard glob syntax: `**` (recursive), `*` (wildcard), `?` (single char)

---

## 🎓 Design Principles

### ✅ **Don't Surprise Me**
- When user specifies a directory, find files in THAT directory
- Don't restrict to `src/` and `tests/` when user clearly wants a different dir
- Sensible defaults based on context

### ✅ **User Control**
- `--include` provides full override capability
- Can combine with `--directory`, `--exclude`, etc.
- CLI always takes precedence over config

### ✅ **Safe Defaults**
- Config defaults (`src/**/*.py`, `tests/**/*.py`) when scanning whole project
- Context-aware defaults (`**/*.py`) when targeting specific directory
- Always Python files only (no other file types by default)

---

## 📚 Related Parameters

### **Include Patterns:**
- `--include` - Override include patterns (CLI)
- Config: `files.include` in `stomper.toml`

### **Exclude Patterns:**
- `--exclude` - Override exclude patterns (CLI)
- Config: `files.exclude` in `stomper.toml`

### **Other File Selection:**
- `--file` - Single file
- `--files` - Multiple files (comma-separated)
- `--directory` - Specific directory
- `--pattern` - Glob pattern
- `--git-changed` - Git changed files
- `--git-staged` - Git staged files
- `--git-diff` - Files changed vs branch

---

## 🧪 Testing

### **Test 1: Directory with Default Patterns**
```bash
stomper fix --directory test_errors/ --dry-run --verbose
# Expected: Finds all .py files in test_errors/
# Result: ✅ Found 3 files
```

### **Test 2: Custom Include Pattern**
```bash
stomper fix --directory src/ --include "**/*.pyi" --dry-run
# Expected: Only finds .pyi files
```

### **Test 3: Override with Include**
```bash
stomper fix --include "**/*.py" --dry-run
# Expected: Finds ALL .py files in project, not just src/ and tests/
```

---

## 📋 Summary

**Old Behavior:**
- ❌ `--directory test_errors/` found 0 files
- ❌ Always used `["src/**/*.py", "tests/**/*.py"]`
- ❌ No way to override from CLI

**New Behavior:**
- ✅ `--directory test_errors/` finds all .py files in that directory
- ✅ Smart precedence: CLI > context > config
- ✅ `--include` parameter for full control
- ✅ Follows "Don't Surprise Me" principle

**Result:** Predictable, user-friendly file discovery! 🎉

