# 🤖 AI Agent: Implement Parallel File Processing in Stomper

## Your Task

Add parallel file processing to the Stomper workflow orchestrator using LangGraph's built-in concurrency features.

---

## 📚 Read These Documents (In Order)

### 1. Main Implementation Guide (START HERE!)
**File:** `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md`
- Complete implementation blueprint
- Exact code examples for Stomper
- **Read this first and completely**

### 2. Complete Working Demo (PROOF IT WORKS!)
**File:** `demo_langgraph_complete_pattern.py`
- **Run it first:** `uv run python demo_langgraph_complete_pattern.py 8 3`
- Shows all 4 features working together
- Has counters that prove concurrency limiting works
- **This is your reference implementation!**

### 3. What's Already Done
**File:** `.agent-os/specs/2024-09-25-week2-ai-agent-integration/sub-specs/task-6-PER-FILE-WORKTREE-COMPLETE.md`
- Per-file worktree architecture is COMPLETE ✅
- Each file already gets isolated environment
- Perfect foundation for parallel processing!

### 4. Complete Overview
**File:** `FINAL-PARALLEL-SUMMARY.md`
- Overview of the complete pattern
- Answers to key questions
- Why this approach is optimal

### 5. Detailed Prompt
**File:** `.agent-os/specs/2024-09-25-week2-ai-agent-integration/PHASE-2-PARALLEL-PROCESSING-PROMPT.md`
- Detailed implementation checklist
- Common pitfalls to avoid
- Success criteria

---

## 🔑 The Four LangGraph Features to Use

### 1. Built-in `max_concurrency` (NO manual semaphore!)
```python
config = {"max_concurrency": 4}
final_state = await graph.ainvoke(initial_state, config=config)
```

### 2. `Annotated` Reducers (automatic aggregation!)
```python
from operator import add
from typing import Annotated

class StomperState(TypedDict, total=False):
    successful_fixes: Annotated[list[str], add]
    total_errors_fixed: Annotated[int, lambda x, y: x + y]
```

### 3. `defer=True` (wait for all branches!)
```python
workflow.add_node("aggregate_results", aggregate_func, defer=True)
```

### 4. `asyncio.Lock` (already have it!)
```python
# Keep the existing diff application lock!
async with self._diff_application_lock:
    apply_to_main(diff)
```

---

## ✅ Implementation Checklist (Quick Version)

### Step 1: Update State (5 min)
In `src/stomper/workflow/state.py`:
- Add `from operator import add`
- Change `successful_fixes: list[str]` → `Annotated[list[str], add]`
- Change `failed_fixes: list[str]` → `Annotated[list[str], add]`
- Change `total_errors_fixed: int` → `Annotated[int, lambda x, y: x + y]`

### Step 2: Update Orchestrator run() Method (5 min)
In `src/stomper/workflow/orchestrator.py`:
```python
async def run(self, config: dict[str, Any]) -> StomperState:
    initial_state = {...}
    
    # ADD THIS:
    run_config = {
        "max_concurrency": self.max_parallel_files,  # ← THE MAGIC!
        "recursion_limit": 100,
    }
    
    final_state = await self.graph.ainvoke(initial_state, config=run_config)
    return final_state
```

### Step 3: OPTIONAL - Add defer=True (2 min)
If you create an aggregation node:
```python
# In _build_graph():
workflow.add_node("aggregate_results", self._aggregate, defer=True)
```

### Step 4: Test (1 hour)
```bash
uv run pytest tests/e2e/test_workflow_integration.py -v -k asyncio
```

**That's it! Seriously!** 🎉

---

## 🎯 What NOT to Do

- ❌ Don't add a manual semaphore (LangGraph has it built-in!)
- ❌ Don't remove the `_diff_application_lock`
- ❌ Don't change the per-file worktree logic
- ❌ Don't break existing tests

---

## 🧪 Verify It Works

### Test 1: Run the Demo
```bash
uv run python demo_langgraph_complete_pattern.py 6 2
```

**Expected:** "Max concurrent tasks reached: 2" (matches config!)

### Test 2: Run Your Tests
```bash
uv run pytest tests/e2e/test_workflow_integration.py -v
```

**Expected:** All tests pass ✅

### Test 3: Add Concurrency Tracking (Like Demo)
See `demo_langgraph_complete_pattern.py` lines 157-169 for how to add counters.

---

## 📊 Expected Performance

With `max_parallel_files=4`:
- **Sequential:** 40 seconds (8 files × 5s)
- **Parallel:** ~12 seconds (2 batches × 5s + overhead)
- **Speedup:** ~3.3x faster! 🚀

---

## 🎊 Why This Will Be Easy

1. **Your foundation is perfect** - Per-file worktrees ready for parallel
2. **LangGraph does the work** - Built-in features handle complexity
3. **Working demos exist** - Copy proven patterns
4. **Minimal code changes** - Mostly annotations and config

**Estimated time:** 2-4 hours (including testing)

---

## 🚀 Getting Started

1. **Run this command to see it work:**
   ```bash
   uv run python demo_langgraph_complete_pattern.py compare
   ```

2. **Read the implementation guide:**
   Open `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md`

3. **Follow the 4-step checklist above**

4. **Test continuously**

5. **Verify with counters** (like the demo)

---

## ✅ Success Criteria

When done:
- ✅ Multiple files process in parallel (up to max_parallel_files)
- ✅ Counters prove concurrency limit works
- ✅ All 273+ tests still pass
- ✅ Performance improvement visible (2-4x)
- ✅ Diff application still serialized
- ✅ No breaking changes

---

## 📁 All Documents Referenced

✅ All verified and correct:

- `PHASE-2-PARALLEL-PROCESSING-PROMPT.md` - Detailed implementation prompt
- `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md` - Implementation guide
- `FINAL-PARALLEL-SUMMARY.md` - Complete overview
- `demo_langgraph_complete_pattern.py` - Working demo (proven!)
- `LANGGRAPH-CONCURRENCY-GUIDE.md` - Technical details
- `PARALLEL-PROCESSING-FAQ.md` - Q&A
- `task-6-PER-FILE-WORKTREE-COMPLETE.md` - Phase 1 completion
- `SESSION-SUMMARY.md` - This session's accomplishments

---

## 🌟 Final Notes

**The hard work is done!** Your per-file worktree refactoring provides the perfect foundation.

Adding parallel processing is now just:
1. Add `Annotated` to 3 state fields (3 lines)
2. Pass `max_concurrency` in config (2 lines)
3. Optionally add `defer=True` (1 parameter)

**That's it!** LangGraph handles the rest! 🎯

---

**Ready to implement? Just follow the steps above!** 🚀

**All documents are verified and working demos prove the concepts!** ✅

