# AI Agent Task: Add Parallel File Processing to Stomper

## 🎯 Your Mission

You are tasked with adding **parallel file processing** to the Stomper workflow orchestrator. The per-file worktree architecture (Phase 1) is complete and provides the perfect foundation. Now you'll enable processing multiple files concurrently using LangGraph's built-in parallel features.

---

## 📚 Required Reading (In Order)

### 1. **Understanding What's Already Done**
- `.agent-os/specs/2024-09-25-week2-ai-agent-integration/sub-specs/task-6-PER-FILE-WORKTREE-COMPLETE.md`
  - The per-file worktree refactoring is COMPLETE ✅
  - Each file already gets its own isolated worktree
  - Diffs are extracted and applied to main workspace
  - This is the perfect foundation for parallelization!

### 2. **How to Implement Parallel Processing (CRITICAL)**
- `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md`
  - **READ THIS COMPLETELY** - your implementation blueprint
  - Shows the complete pattern with all 4 LangGraph features
  - Includes exact code examples for Stomper

### 3. **Complete Pattern Demo (WORKING PROOF)**
- `demo_langgraph_complete_pattern.py`
  - **Run this to see it work:** `uv run python demo_langgraph_complete_pattern.py 8 3`
  - Shows all 4 features working together
  - Has counters that PROVE concurrency limiting works
  - This is your reference implementation!

### 4. **Understanding Concurrency**
- `FINAL-PARALLEL-SUMMARY.md`
  - Answers to key questions about parallel processing
  - Comparison of approaches
  - Why we use LangGraph's built-in features

### 5. **Technical Deep Dive (Optional)**
- `LANGGRAPH-CONCURRENCY-GUIDE.md` - How concurrency control works
- `PARALLEL-PROCESSING-FAQ.md` - Common questions answered

---

## 🔑 The Four LangGraph Features You'll Use

### **Feature 1: Built-in `max_concurrency`**
```python
# NO manual semaphore needed!
config = {"max_concurrency": 4}
final_state = await graph.ainvoke(initial_state, config=config)
```

**Source:** [LangGraph _executor.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/_executor.py#L131-L140)

### **Feature 2: `Annotated` Reducers**
```python
from operator import add
from typing import Annotated

class StomperState(TypedDict, total=False):
    successful_fixes: Annotated[list[str], add]  # Auto-concatenate
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Auto-sum
```

### **Feature 3: `defer=True`**
```python
# Aggregate node waits for ALL parallel branches to complete
workflow.add_node("aggregate_results", aggregate_func, defer=True)
```

### **Feature 4: `asyncio.Lock` (Already Have!)**
```python
# Keep the existing diff application lock!
async with self._diff_application_lock:
    apply_to_main(diff)
    commit_in_main(file)
```

---

## ✅ Implementation Checklist

### Phase 1: Update State Definitions (30 min)

**File:** `src/stomper/workflow/state.py`

- [ ] Add `from operator import add` import
- [ ] Update `StomperState` fields to use `Annotated` reducers:
  ```python
  successful_fixes: Annotated[list[str], add]
  failed_fixes: Annotated[list[str], add]
  total_errors_fixed: Annotated[int, lambda x, y: x + y]
  
  # Optional: Add metrics aggregation
  file_metrics: Annotated[list[dict[str, Any]], add]
  ```
- [ ] Add `current_file: FileState | None` for parallel processing

### Phase 2: Update Orchestrator (2-3 hours)

**File:** `src/stomper/workflow/orchestrator.py`

- [ ] **Remove manual semaphore** (if you have one) - not needed!
- [ ] **Keep the diff application lock** - still needed for critical section

- [ ] **Update `_build_graph()` method:**
  ```python
  # Add defer=True to aggregation (if you have one)
  # Or simplify the graph to use Send() pattern
  
  # Option A: Keep current sequential flow (works as-is)
  # Option B: Add parallel mode with Send() pattern (see guide)
  ```

- [ ] **Create parallel-mode graph builder** (optional):
  ```python
  def _build_parallel_graph(self):
      workflow = StateGraph(StomperState)
      
      # Sequential setup
      workflow.add_node("initialize", self._initialize_session)
      workflow.add_node("collect_errors", self._collect_all_errors)
      
      # Parallel processing
      workflow.add_node("process_file", self._process_single_file_parallel)
      workflow.add_node("aggregate", self._aggregate_results, defer=True)
      workflow.add_node("cleanup", self._cleanup_session)
      
      # Edges
      workflow.add_edge(START, "initialize")
      workflow.add_edge("initialize", "collect_errors")
      workflow.add_conditional_edges("collect_errors", self._fan_out_files)
      workflow.add_edge("process_file", "aggregate")
      workflow.add_edge("aggregate", "cleanup")
      workflow.add_edge("cleanup", END)
      
      return workflow.compile()
  ```

- [ ] **Add `_fan_out_files()` method:**
  ```python
  def _fan_out_files(self, state: StomperState):
      """Fan out to parallel file processing."""
      files = state.get("files", [])
      
      if not files:
          return "aggregate"
      
      return [
          Send("process_file", {
              **state,
              "current_file": file,
          })
          for file in files
      ]
  ```

- [ ] **Create `_process_single_file_parallel()` method:**
  ```python
  async def _process_single_file_parallel(self, state: dict) -> dict:
      """Process one file in parallel (LangGraph handles concurrency)."""
      file = state["current_file"]
      session_id = state["session_id"]
      
      # NO SEMAPHORE! max_concurrency config handles this
      
      try:
          # Same per-file logic as current implementation:
          # 1. Create worktree
          # 2. Generate prompt  
          # 3. Call agent
          # 4. Verify fixes
          # 5. Run tests
          # 6. Extract diff
          # 7. Apply to main (WITH LOCK!)
          # 8. Commit in main (WITH LOCK!)
          # 9. Destroy worktree
          
          # Return for aggregation
          return {
              "successful_fixes": [str(file.file_path)],
              "total_errors_fixed": len(fixed_errors),
          }
      except Exception as e:
          return {"failed_fixes": [str(file.file_path)]}
  ```

- [ ] **Update `run()` method:**
  ```python
  async def run(self, config: dict[str, Any]) -> StomperState:
      initial_state = {...}
      
      # THE MAGIC: Set max_concurrency in config!
      run_config = {
          "max_concurrency": self.max_parallel_files,
          "recursion_limit": 100,
      }
      
      return await self.graph.ainvoke(initial_state, config=run_config)
  ```

### Phase 3: Update Configuration (15 min)

**File:** `src/stomper/config/models.py`

Already has the fields! Just verify:
- [ ] `max_parallel_files: int = Field(default=4, ge=1, le=16)` ✅
- [ ] `parallel_mode: bool = Field(default=False)` (optional)

### Phase 4: Testing (1-2 hours)

**File:** `tests/e2e/test_workflow_integration.py`

- [ ] **Add test for parallel mode:**
  ```python
  @pytest.mark.e2e
  async def test_workflow_parallel_processing(tmp_path):
      """Test parallel file processing."""
      # Setup 4 files with errors
      for i in range(1, 5):
          file = tmp_path / f"file{i}.py"
          file.write_text(f"import os  # F401\n")
      
      # Initialize git repo
      subprocess.run(["git", "init"], cwd=tmp_path, check=True)
      # ... git setup ...
      
      # Create workflow with parallel mode
      workflow = StomperWorkflow(
          project_root=tmp_path,
          max_parallel_files=2,
          use_sandbox=True,
          run_tests=False,
      )
      
      test_agent = MockAIAgent(return_value="")
      workflow.register_agent("cursor-cli", test_agent)
      
      # Run workflow
      final_state = await workflow.run({"enabled_tools": ["ruff"]})
      
      # Verify all files processed
      assert len(final_state["successful_fixes"]) == 4
      assert final_state["status"] == ProcessingStatus.COMPLETED
  ```

- [ ] **Run existing tests** to ensure no regression:
  ```bash
  uv run pytest tests/e2e/test_workflow_integration.py -v -k asyncio
  ```

### Phase 5: Verification (30 min)

- [ ] Run unit tests: `uv run pytest tests/unit/ -v`
- [ ] Run E2E tests: `uv run pytest tests/e2e/test_workflow_integration.py -v`
- [ ] Verify 273+ tests still pass
- [ ] Manual test with 5-10 files to verify parallel execution
- [ ] Check that max_concurrent_files config actually limits concurrency

---

## 🚨 Critical Requirements

### Must Do:
- ✅ Use `config={"max_concurrency": N}` (NO manual semaphore!)
- ✅ Use `Annotated[list, add]` for result aggregation
- ✅ Use `defer=True` on aggregation node (if you add one)
- ✅ KEEP the `_diff_application_lock` (critical section!)
- ✅ Each file still gets its own worktree (don't change this!)
- ✅ Verify with counters (like the demo) that concurrency limit works

### Must NOT Do:
- ❌ Don't add a manual semaphore (LangGraph has it built-in!)
- ❌ Don't remove the diff application lock
- ❌ Don't share worktrees between files
- ❌ Don't break existing tests
- ❌ Don't forget `defer=True` if you add an aggregation node

---

## 🎨 Two Implementation Approaches

### **Approach A: Sequential with Parallel Option** (Recommended)

Keep the current sequential workflow as default, add parallel as optional:

```python
class StomperWorkflow:
    def __init__(self, max_parallel_files: int = 1):  # Default: sequential
        self.max_parallel_files = max_parallel_files
        
        if max_parallel_files > 1:
            self.graph = self._build_parallel_graph()
        else:
            self.graph = self._build_graph()  # Current sequential
```

**Pros:**
- ✅ Backwards compatible
- ✅ Safe default (sequential)
- ✅ Users opt-in to parallel mode

### **Approach B: Always Parallel** (Simpler)

Use parallel architecture always (even with max_parallel_files=1):

```python
class StomperWorkflow:
    def __init__(self, max_parallel_files: int = 4):  # Default: parallel
        self.graph = self._build_graph()  # Parallel-capable
        
    async def run(self, config):
        run_config = {
            "max_concurrency": self.max_parallel_files,  # Works with 1!
        }
        return await self.graph.ainvoke(initial_state, config=run_config)
```

**Pros:**
- ✅ Simpler (one graph implementation)
- ✅ max_concurrency=1 = sequential (automatic)
- ✅ Less code to maintain

**Recommendation:** Use Approach B (simpler and cleaner)

---

## 🧪 How to Verify It Works

### Test 1: Run the Working Demo
```bash
# See the pattern in action
uv run python demo_langgraph_complete_pattern.py 10 4

# Compare concurrency levels
uv run python demo_langgraph_complete_pattern.py compare
```

**Expected:** Peak concurrent = exactly what you set in config

### Test 2: Add Concurrency Tracking (Like Demo)
```python
class StomperWorkflow:
    def __init__(self):
        self._active_files = 0
        self._peak_concurrent = 0
        self._active_lock = asyncio.Lock()
    
    async def _process_single_file_parallel(self, state):
        async with self._active_lock:
            self._active_files += 1
            if self._active_files > self._peak_concurrent:
                self._peak_concurrent = self._active_files
            logger.info(f"Active: {self._active_files}, Peak: {self._peak_concurrent}")
        
        try:
            # ... process file ...
            pass
        finally:
            async with self._active_lock:
                self._active_files -= 1
```

**Expected:** Peak should never exceed `max_parallel_files` config

### Test 3: Create Test Project
```bash
# Create project with 10 files with errors
# Run: stomper fix --max-parallel-files 3
# Observe: Only 3 files processing at once
# Verify: All 10 files get fixed
```

---

## 💡 Key Insights from Research

### Discovery 1: LangGraph Has Built-in Concurrency
- Found in source code: `_executor.py`
- Uses semaphore internally when `max_concurrency` is set
- **You don't need to build your own!**

### Discovery 2: `Annotated` Reducers for Aggregation
```python
# Each parallel file returns:
{"successful_fixes": ["auth.py"]}

# LangGraph automatically merges:
successful_fixes = ["auth.py", "models.py", "utils.py"]
```

### Discovery 3: `defer=True` for Proper Fan-In
```python
# Without defer: Aggregate might run before all files done
# With defer: Aggregate waits for ALL files ✅
workflow.add_node("aggregate", aggregate_func, defer=True)
```

### Discovery 4: Lock Still Needed for Critical Sections
```python
# LangGraph can't know what needs serialization
# You must explicitly lock critical sections:
async with self._diff_application_lock:
    apply_to_main(diff)  # Only 1 at a time!
```

---

## 🎯 Success Criteria

You'll know you're done when:

- ✅ Multiple files process in parallel (up to max_parallel_files)
- ✅ Diff application is still serialized (one at a time)
- ✅ Results are automatically aggregated from all parallel branches
- ✅ All existing tests still pass (273+ tests)
- ✅ New parallel test passes
- ✅ Manual test shows N files processing concurrently
- ✅ Counters prove actual concurrency matches config
- ✅ Performance improvement visible (2-4x speedup with 4 concurrent)

---

## 🎨 Minimal Changes Required

The beauty of your current architecture: **Minimal changes needed!**

### Changes to Make:

1. **State fields** - Add `Annotated` (1 line per field)
2. **Graph structure** - Use `Send()` for fan-out (1 method)
3. **Run method** - Pass `max_concurrency` config (2 lines)
4. **Aggregation** - Add `defer=True` if creating aggregate node (1 parameter)

### Don't Change:

- ✅ Per-file worktree logic (perfect as-is!)
- ✅ Diff application lock (keep it!)
- ✅ Error handling
- ✅ Test infrastructure
- ✅ Component initialization

**Estimated time:** 2-4 hours (most time is testing!)

---

## 📝 Step-by-Step Implementation

### Step 1: Update State (30 min)

In `src/stomper/workflow/state.py`:

```python
from operator import add
from typing import Annotated

class StomperState(TypedDict, total=False):
    # ... existing fields ...
    
    # UPDATE these fields to use reducers:
    successful_fixes: Annotated[list[str], add]  # Changed!
    failed_fixes: Annotated[list[str], add]      # Changed!
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Changed!
    
    # ADD this for parallel processing:
    current_file: FileState | None
```

### Step 2: Add Fan-Out Method (15 min)

In `src/stomper/workflow/orchestrator.py`:

```python
def _fan_out_files(self, state: StomperState):
    """Fan out to parallel file processing."""
    from langgraph.types import Send
    
    files = state.get("files", [])
    
    if not files:
        logger.info("No files to process")
        return "cleanup"  # Or "aggregate" if you have one
    
    logger.info(f"Fanning out to {len(files)} parallel workers")
    
    return [
        Send("process_file_parallel", {
            **state,
            "current_file": file,
        })
        for file in files
    ]
```

### Step 3: Create or Adapt Parallel Processing Node (1 hour)

**Option A:** Keep current nodes, just call them sequentially per file:

```python
async def _process_single_file_parallel(self, state: dict) -> dict:
    """Process one file (called in parallel by LangGraph)."""
    file = state["current_file"]
    
    # Create a mini-state for this file
    file_state = {**state, "current_file_index": 0, "files": [file]}
    
    # Run the existing per-file nodes in sequence:
    # create_worktree → generate_prompt → call_agent → 
    # verify → test → extract_diff → apply_to_main (LOCKED) → 
    # commit (LOCKED) → destroy_worktree
    
    # (Your existing nodes already do this!)
    
    # Return aggregated results
    return {
        "successful_fixes": [str(file.file_path)],
        "total_errors_fixed": len(file.fixed_errors),
    }
```

**Option B:** Create new consolidated node (see STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md)

### Step 4: Update run() Method (5 min)

```python
async def run(self, config: dict[str, Any]) -> StomperState:
    initial_state: StomperState = {...}
    
    # Add max_concurrency to config
    run_config = {
        "max_concurrency": self.max_parallel_files,  # ← THE MAGIC!
        "recursion_limit": 100,
    }
    
    logger.info(f"Starting workflow (max_parallel: {self.max_parallel_files})")
    
    final_state = await self.graph.ainvoke(initial_state, config=run_config)
    
    return final_state
```

### Step 5: Test & Verify (1-2 hours)

Run tests and verify everything works!

---

## 🔬 Reference Implementation

**See:** `demo_langgraph_complete_pattern.py` lines 146-205

This shows EXACTLY how to:
- Track active concurrent tasks
- Use no manual semaphore
- Apply locks for critical sections
- Return results for aggregation

**The demo proves it works!** Run it to see.

---

## 🎛️ Configuration Usage

After implementation, users can control parallelism:

```bash
# Sequential (safe default)
stomper fix --max-parallel-files 1

# Low concurrency (conservative)
stomper fix --max-parallel-files 2

# Medium concurrency (recommended)
stomper fix --max-parallel-files 4

# High concurrency (aggressive)
stomper fix --max-parallel-files 8
```

In config file:
```toml
[tool.stomper.workflow]
max_parallel_files = 4
```

---

## 🐛 Common Pitfalls to Avoid

### Pitfall 1: Forgetting `defer=True`
```python
# ❌ WRONG: Aggregate might run before all files done
workflow.add_node("aggregate", aggregate_func)

# ✅ RIGHT: Aggregate waits for all files
workflow.add_node("aggregate", aggregate_func, defer=True)
```

### Pitfall 2: Missing Annotated Reducer
```python
# ❌ WRONG: Error "Can receive only one value per step"
successful_fixes: list[str]

# ✅ RIGHT: Automatic merge
successful_fixes: Annotated[list[str], add]
```

### Pitfall 3: Removing the Lock
```python
# ❌ WRONG: Race conditions in git operations!
apply_to_main(diff)

# ✅ RIGHT: Serialize critical section
async with self._diff_application_lock:
    apply_to_main(diff)
```

### Pitfall 4: Adding Manual Semaphore
```python
# ❌ WRONG: Conflicts with LangGraph's built-in
self._semaphore = asyncio.Semaphore(max_files)

# ✅ RIGHT: Just use config
config = {"max_concurrency": max_files}
```

---

## 📊 Expected Performance

With `max_parallel_files=4`:

| Scenario | Sequential Time | Parallel Time | Speedup |
|----------|----------------|---------------|---------|
| 4 files | 20s | 6-8s | ~3x |
| 8 files | 40s | 12-15s | ~3x |
| 16 files | 80s | 24-30s | ~3x |

**Note:** Speedup limited by:
- Critical section (diff application)
- I/O operations (git, file system)
- AI agent response time variance

Typical speedup: **2-4x with 4 concurrent files**

---

## 🎓 Learning Resources

### Working Demos (Run These!)
```bash
# Complete pattern (all 4 features)
uv run python demo_langgraph_complete_pattern.py 8 3

# Compare concurrency levels
uv run python demo_langgraph_complete_pattern.py compare

# Built-in concurrency only
uv run python demo_langgraph_builtin_concurrency.py 6 2
```

### Documentation
- `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md` - Your implementation blueprint
- `FINAL-PARALLEL-SUMMARY.md` - Complete overview
- `LANGGRAPH-CONCURRENCY-GUIDE.md` - Deep technical dive

---

## ✅ Acceptance Criteria

When complete, the system should:

- [ ] Process multiple files in parallel (up to max_parallel_files)
- [ ] Never exceed max_parallel_files concurrent tasks
- [ ] Serialize diff application (lock ensures this)
- [ ] Automatically aggregate results from all files
- [ ] Wait for all files before final aggregation (defer=True)
- [ ] Pass all existing tests (273+)
- [ ] Show performance improvement (2-4x speedup)
- [ ] Work with max_parallel_files=1 (sequential, backwards compatible)
- [ ] Properly handle errors in parallel tasks
- [ ] Clean up all worktrees (even on errors)

---

## 🚀 Quick Start

1. **Run the demo to understand the pattern:**
   ```bash
   uv run python demo_langgraph_complete_pattern.py 8 3
   ```

2. **Read the implementation guide:**
   Open `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md`

3. **Follow the checklist above** step by step

4. **Test continuously** as you implement each phase

5. **Verify with counters** (like the demo) that it works

---

## 🎊 Final Notes

**Your Foundation is Perfect!**

The per-file worktree refactoring you completed provides:
- ✅ True file isolation (each file = own worktree)
- ✅ Atomic operations per file
- ✅ Clean separation of concerns
- ✅ Perfect for parallelization!

**Adding Parallel is Easy!**

Just add:
1. `Annotated` reducers (2 minutes)
2. `Send()` fan-out (10 minutes)
3. `max_concurrency` config (2 minutes)
4. `defer=True` if needed (1 minute)

**Most time will be testing and verification!**

---

## 🌟 What Makes This The "Google Way"

1. **Leverage the framework** - Use LangGraph's built-in features
2. **Don't reinvent wheels** - No manual semaphore needed
3. **Observable** - LangGraph + LangSmith integration
4. **Tested** - Working demos prove the pattern
5. **Maintainable** - Less code, clear intent

---

**Good luck! You have everything you need!** 🚀

**The demos prove the pattern works, and your architecture is perfect for it!** 🌟

