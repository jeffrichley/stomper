# 🐛 Debugging Stomper Parallel Workflow in Cursor IDE

## Quick Start

### 1. **Open Debug Panel**
- Press `Ctrl+Shift+D` (Windows/Linux) or `Cmd+Shift+D` (Mac)
- Or click the "Run and Debug" icon in the sidebar

### 2. **Select Configuration**
Choose from the dropdown at the top:
- **"Debug Stomper - Sequential"** - Easiest to debug (1 file at a time)
- **"Debug Stomper - Parallel Workflow"** - See parallel execution (2 files)
- **"Debug Custom Script"** - Debug using `debug_parallel_workflow.py`

### 3. **Set Breakpoints**
Click to the left of line numbers in these files:

#### **In `src/stomper/workflow/orchestrator.py`:**
- **Line 668** - `_fan_out_files()` - See Send() creation
- **Line 297** - `_process_single_file_complete()` - See file processing start
- **Line 690** - Critical section (Git lock)
- **Line 563** - `_aggregate_results()` - See merged results

### 4. **Press F5** to start debugging!

---

## 📋 Available Configurations

### 1. **Debug Stomper - Sequential (1 file at a time)**
```json
"max_parallel_files": "1"
```
- Processes files one at a time
- **EASIEST to debug** - no parallelism
- Good for understanding the flow

### 2. **Debug Stomper - Parallel Workflow (2 files)**
```json
"max_parallel_files": "2"
```
- Processes 2 files simultaneously
- See parallelism in action
- Uses sandbox mode (Git worktrees)

### 3. **Debug Stomper - Current File**
- Debugs the file you have open in editor
- Quick way to test single file

### 4. **Debug Stomper - No Sandbox (Direct Mode)**
- Modifies files directly (no Git worktrees)
- Simpler execution path
- Good for understanding core logic

### 5. **Debug Stomper - On Stomper Itself**
- Run Stomper on its own codebase
- Real-world testing

### 6. **Debug Custom Script**
- Uses `debug_parallel_workflow.py`
- Full control over configuration
- Can modify script for different tests

---

## 🎯 Key Breakpoint Locations

### **Understanding the Flow:**

1. **Start: `orchestrator.py:668` - Fan-Out**
   ```python
   return [
       Send("process_single_file", {  # ← BREAKPOINT
           **state,
           "current_file": file,
       })
       for file in files
   ]
   ```
   - See list of Send() objects created
   - Each Send() = one file to process
   - Watch: `files` variable to see all files

2. **Parallel Processing: `orchestrator.py:297`**
   ```python
   async def _process_single_file_complete(self, state: dict) -> dict:
       # ← BREAKPOINT
       current_file = state["current_file"]
   ```
   - Each parallel branch enters here
   - Watch: `current_file` to see which file this branch is processing
   - Watch: `state` to see branch-specific state

3. **Critical Section: `orchestrator.py:690`**
   ```python
   async with self._diff_application_lock:
       logger.info(f"🔒 [LOCKED]...")  # ← BREAKPOINT
   ```
   - See serialized Git operations
   - Only one branch at a time can enter
   - Watch: How lock prevents conflicts

4. **Aggregation: `orchestrator.py:563`**
   ```python
   async def _aggregate_results(self, state: StomperState) -> StomperState:
       # ← BREAKPOINT
       successful = state.get("successful_fixes", [])
   ```
   - See all results merged together
   - Watch: `successful_fixes` list with all files
   - This runs AFTER all parallel branches complete (defer=True)

---

## 🔍 Debugging Tips

### **Watch Variables**
Add these to the Watch panel (Debug sidebar):
```python
state["current_file"].file_path        # Current file being processed
state["successful_fixes"]              # List of fixed files
len(state["files"])                    # Total files to process
self.max_parallel_files                # Concurrency limit
```

### **Conditional Breakpoints**
Right-click breakpoint → "Edit Breakpoint" → Add condition:
```python
# Only break for specific file
current_file.file_path.name == "test1.py"

# Only break when lock is acquired
True  # (with log message)
```

### **Step Through Controls**
- **F10** - Step Over (execute current line)
- **F11** - Step Into (go inside function)
- **Shift+F11** - Step Out (exit current function)
- **F5** - Continue (run to next breakpoint)

### **Debug Console**
While paused, type in Debug Console:
```python
# Inspect variables
current_file.file_path
state.keys()
len(state["files"])

# Check state
print(state["successful_fixes"])
print(f"File: {current_file.file_path}, Errors: {len(current_file.errors)}")
```

---

## 📝 Modifying Test Configurations

### **In `debug_parallel_workflow.py`:**

```python
# Test different scenarios by changing config:

config = {
    # Sequential execution (easy to debug)
    "max_parallel_files": 1,
    
    # Parallel execution (see concurrency)
    "max_parallel_files": 2,
    
    # Direct mode (no Git worktrees)
    "use_sandbox": False,
    
    # With worktrees (more complex)
    "use_sandbox": True,
    
    # Different tools
    "enabled_tools": ["ruff"],        # Just Ruff
    "enabled_tools": ["ruff", "mypy"], # Multiple tools
}
```

### **In `.vscode/launch.json`:**

Add custom configuration:
```json
{
  "name": "My Custom Debug",
  "type": "debugpy",
  "request": "launch",
  "module": "stomper",
  "args": [
    "fix",
    "my_project/",           // Your directory
    "--tools", "ruff",
    "--max-parallel-files", "1",
    "--use-sandbox"
  ],
  "console": "integratedTerminal",
  "justMyCode": false
}
```

---

## 🧪 Test Files Created

Three test files with intentional errors:
- `test_errors/test1.py` - Import and spacing errors
- `test_errors/test2.py` - Multiple imports, long lines
- `test_errors/test3.py` - Various formatting issues

**To see errors before fixing:**
```bash
uv run ruff check test_errors/
```

---

## 🚀 Quick Commands

### **Debug with breakpoints:**
1. Open `src/stomper/workflow/orchestrator.py`
2. Set breakpoint at line 668 (_fan_out_files)
3. Press F5
4. Select "Debug Stomper - Sequential"

### **Debug custom script:**
1. Open `debug_parallel_workflow.py`
2. Set breakpoint at line 56 (`result = await workflow.run(config)`)
3. Press F5
4. Select "Debug Custom Script"

### **Debug current file:**
1. Open any Python file with errors
2. Press F5
3. Select "Debug Stomper - Current File"

---

## 📊 Understanding Parallel Execution

### **Sequential (max_parallel_files=1):**
```
Time →
File 1: ████████████ (processes)
File 2:             ████████████ (waits, then processes)
File 3:                         ████████████ (waits, then processes)
```

### **Parallel (max_parallel_files=2):**
```
Time →
File 1: ████████████ (processes in parallel)
File 2: ████████████ (processes in parallel)
File 3:             ████████████ (waits for slot, then processes)
```

Set breakpoint at `_process_single_file_complete` to see multiple files enter simultaneously!

---

## ❓ Troubleshooting

### **Breakpoints not hitting?**
- Make sure `"justMyCode": false` in launch.json
- Check that PYTHONPATH is set correctly
- Try reloading window (Ctrl+Shift+P → "Reload Window")

### **Can't see variables?**
- Switch to "Variables" panel in Debug sidebar
- Add to "Watch" for persistent monitoring
- Use Debug Console to inspect

### **Process exits immediately?**
- Check that test_errors/ directory exists
- Verify test files have errors: `uv run ruff check test_errors/`
- Check terminal output for error messages

---

## 🎓 Learning Path

### **Day 1: Sequential Flow**
- Use "Debug Stomper - Sequential" configuration
- Set breakpoints at each major step
- Understand single file processing

### **Day 2: Parallel Execution**
- Use "Debug Stomper - Parallel Workflow"
- Watch how Send() creates separate branches
- See how results merge

### **Day 3: Advanced**
- Use conditional breakpoints
- Modify debug script for custom scenarios
- Debug on real projects

---

**Happy Debugging! 🐛🔍**

For more help, see:
- `SEND-API-STATE-ISOLATION-EXPLAINED.md` - How state isolation works
- `PHASE-2-PARALLEL-COMPLETE.md` - Implementation details

