# 🐛 Debug Configurations Guide

## 📋 Available Configurations

Press **F5** in Cursor IDE and select from **9 debug configurations**:

---

### **1. Debug Stomper - Parallel Workflow (2 files)** ⚡
```json
--directory test_errors/
--ruff --no-mypy
--max-parallel-files 2
--use-sandbox --no-run-tests
```

**Use When:** 
- Testing parallel processing with 2 files
- Watching Send() API in action
- Debugging sandbox mode

**Breakpoints:** 
- `orchestrator.py:668` - Fan-out (Send creation)
- `orchestrator.py:297` - Parallel file processing

---

### **2. Debug Stomper - Sequential (1 file at a time)** 🐢
```json
--directory test_errors/
--ruff --no-mypy
--max-parallel-files 1
--use-sandbox --no-run-tests
```

**Use When:**
- Easy step-through debugging
- Understanding workflow flow
- Debugging individual file processing

**Best For:** First-time debugging

---

### **3. Debug Stomper - Current File** 📄
```json
--file ${file}
--ruff --no-mypy
--max-parallel-files 1 --no-run-tests
```

**Use When:**
- Testing on the file you have open
- Quick iteration on a specific file
- Debugging file-specific issues

**How:** Open any `.py` file and press F5

---

### **4. Debug Stomper - Custom Include Patterns** 🎯
```json
--directory test_errors/
--include "**/*.py,**/*.pyi"
--ruff --no-mypy
--max-parallel-files 2 --no-use-sandbox --no-run-tests
```

**Use When:**
- Testing `--include` parameter
- Custom file pattern matching
- Including stub files (`.pyi`)

**Demonstrates:** New include pattern feature

---

### **5. Debug Stomper - With Exclude Patterns** 🚫
```json
--directory src/
--exclude "**/migrations/**,**/__pycache__/**"
--ruff --no-mypy
--max-parallel-files 4 --use-sandbox --no-run-tests
```

**Use When:**
- Testing exclusion patterns
- Skipping migrations/cache files
- Complex filtering scenarios

**Demonstrates:** Exclude pattern feature

---

### **6. Debug Stomper - No Sandbox (Direct Mode)** 🔓
```json
--directory test_errors/
--ruff --no-mypy
--no-use-sandbox --no-run-tests
--max-parallel-files 2
```

**Use When:**
- Faster execution (no Git worktrees)
- Debugging without sandbox overhead
- Testing direct file modification

**Warning:** Modifies files directly!

---

### **7. Debug Stomper - Multiple Tools** 🛠️
```json
--directory test_errors/
--ruff --mypy
--max-parallel-files 2
--use-sandbox --no-run-tests
```

**Use When:**
- Testing with both Ruff and MyPy
- Complex error scenarios
- Multi-tool integration

---

### **8. Debug Stomper - On Stomper Itself** 🔄
```json
--directory src/stomper/
--ruff --no-mypy
--max-parallel-files 2
--use-sandbox --no-run-tests
```

**Use When:**
- Dogfooding (testing on Stomper itself)
- Real-world testing
- Finding issues in production code

**Note:** Uses Stomper to fix Stomper!

---

### **9. Debug Custom Script** 🎛️
```python
program: debug_parallel_workflow.py
```

**Use When:**
- Full control over configuration
- Testing specific scenarios
- Custom workflow setup

**Modify:** Edit `debug_parallel_workflow.py` for custom configs

---

## 🎯 Quick Selection Guide

### **I want to...**

#### **Understand the basics**
→ Use **#2: Sequential** (easiest to follow)

#### **See parallel processing**
→ Use **#1: Parallel Workflow** (2 files at once)

#### **Test include/exclude patterns**
→ Use **#4: Custom Include** or **#5: With Exclude**

#### **Debug current file quickly**
→ Use **#3: Current File**

#### **Test without sandbox**
→ Use **#6: No Sandbox (Direct Mode)**

#### **Test on real code**
→ Use **#8: On Stomper Itself**

---

## 🔑 Key Parameters Explained

### **File Selection:**
- `--file` - Single file
- `--directory` - All files in directory
- `--include` - Custom patterns (e.g., `**/*.py,**/*.pyi`)
- `--exclude` - Exclusion patterns

### **Workflow Control:**
- `--max-parallel-files N` - Concurrency (1=sequential, 2+=parallel)
- `--use-sandbox` / `--no-use-sandbox` - Git worktree isolation
- `--run-tests` / `--no-run-tests` - Test validation

### **Tools:**
- `--ruff` / `--no-ruff` - Ruff linter
- `--mypy` / `--no-mypy` - MyPy type checker

---

## 📍 Key Breakpoint Locations

### **For Understanding Parallel Flow:**
```python
# 1. Fan-out (Send creation)
src/stomper/workflow/orchestrator.py:668

# 2. Parallel file processing starts
src/stomper/workflow/orchestrator.py:297

# 3. Critical section (Git lock)
src/stomper/workflow/orchestrator.py:690

# 4. Aggregation (results merged)
src/stomper/workflow/orchestrator.py:563
```

### **For Understanding File Discovery:**
```python
# Include pattern precedence
src/stomper/cli.py:509-518

# Directory scanning
src/stomper/cli.py:541-549
```

---

## 🎬 Usage

### **Step 1: Open Stomper in Cursor**
```bash
cd E:\workspaces\ai\tools\stomper
code .
```

### **Step 2: Set Breakpoints** (Optional)
Click left of line numbers in:
- `src/stomper/workflow/orchestrator.py`
- `src/stomper/cli.py`

### **Step 3: Press F5**
- Debug panel opens
- Select a configuration
- Debugger starts!

### **Step 4: Debug Controls**
- **F10** - Step Over
- **F11** - Step Into
- **F5** - Continue
- **Shift+F5** - Stop

---

## 💡 Tips

### **Tip 1: Start Simple**
Begin with **#2: Sequential** to understand the flow, then try **#1: Parallel**.

### **Tip 2: Watch Variables**
Add to Watch panel:
```python
state["current_file"].file_path
state["successful_fixes"]
self.max_parallel_files
```

### **Tip 3: Conditional Breakpoints**
Right-click breakpoint → Edit → Condition:
```python
current_file.file_path.name == "test1.py"
```

### **Tip 4: Use Debug Console**
While paused, type:
```python
print(state.keys())
len(state["files"])
current_file.file_path
```

### **Tip 5: Modify and Reload**
After editing code:
1. Stop debugger (Shift+F5)
2. Press F5 again
3. Select same/different configuration

---

## 🆕 New in This Update

### **Added Configurations:**
✅ **Custom Include Patterns** - Demonstrates `--include` parameter  
✅ **With Exclude Patterns** - Demonstrates `--exclude` parameter

### **Fixed:**
✅ **Current File** - Now uses `--file ${file}` correctly  
✅ **All Configs** - Use `--directory` flag properly

### **Updated:**
✅ All configs use new CLI parameters (--max-parallel-files, --use-sandbox, etc.)  
✅ Include pattern precedence working correctly

---

## 📚 Related Documentation

- `QUICK-DEBUG-START.md` - Quick start guide
- `DEBUG-GUIDE.md` - Complete debugging guide
- `INCLUDE-PATTERN-PRECEDENCE.md` - File pattern documentation
- `CLI-UPGRADE-COMPLETE.md` - CLI parameters reference

---

**Happy Debugging! 🐛🔍**

Select a configuration, press F5, and start exploring! 🚀

