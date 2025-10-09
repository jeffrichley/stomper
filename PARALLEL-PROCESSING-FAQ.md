# Parallel Processing FAQ - Your Questions Answered! 🎯

## ❓ Question 1: How Do We Aggregate Information?

### The Problem
When LangGraph runs tasks in parallel, each branch returns its own state. How do we collect all the results?

### The Solution: `Annotated` with Reducers!

```python
from operator import add
from typing import Annotated

class StomperState(TypedDict, total=False):
    # ✅ Annotated tells LangGraph HOW to merge results
    successful_fixes: Annotated[list[str], add]  # Concatenate lists
    failed_fixes: Annotated[list[str], add]      # Concatenate lists
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Sum integers
```

**How it works:**
1. Task 1 returns: `{"successful_fixes": ["auth.py"]}`
2. Task 2 returns: `{"successful_fixes": ["models.py"]}`
3. Task 3 returns: `{"successful_fixes": ["utils.py"]}`
4. LangGraph merges using `add`: `["auth.py", "models.py", "utils.py"]` ✅

### Built-in Reducers

LangGraph provides several reducers:

```python
from operator import add

# Concatenate lists (most common)
results: Annotated[list[str], add]

# Sum numbers
total_count: Annotated[int, lambda x, y: x + y]

# Custom reducer
metrics: Annotated[dict, lambda old, new: {**old, **new}]  # Merge dicts
```

### Example in Your Code

```python
async def _process_single_file_parallel(self, state: dict) -> dict:
    """Process one file in parallel."""
    file = state["current_file"]
    
    # ... process file ...
    
    # Return results - LangGraph aggregates automatically!
    return {
        "successful_fixes": [str(file.file_path)],  # ← Will be concatenated
        "total_errors_fixed": len(fixed_errors),    # ← Will be summed
    }

# After all parallel branches complete, state contains:
# successful_fixes = ["file1.py", "file2.py", "file3.py"]
# total_errors_fixed = 5 + 3 + 7 = 15
```

---

## ❓ Question 2: Why Use Semaphore if LangGraph Can Handle It?

### The Short Answer
**LangGraph CANNOT limit concurrency - you NEED the semaphore!**

### The Long Answer

**What LangGraph's Send() Does:**
```python
# This launches ALL 100 tasks immediately into the async event loop
return [Send("process_file", {...}) for file in 100_files]
```

**What Happens Without Semaphore:**
- 💥 100 worktrees created simultaneously
- 💥 100 AI agent calls at once
- 💥 System runs out of resources
- 💥 API rate limits exceeded

**What Happens With Semaphore:**
```python
self._semaphore = asyncio.Semaphore(4)  # Only 4 slots

async def _process_single_file(self, state):
    async with self._semaphore:  # Acquire slot (wait if full)
        # Only 4 tasks can be here at once
        # The other 96 wait in queue
        await process_file()
```

### LangGraph vs Semaphore Responsibilities

| Concern | Who Handles It | How |
|---------|---------------|-----|
| Parallel execution | LangGraph | `Send()` API |
| State merging | LangGraph | `Annotated[..., add]` |
| Waiting for all branches | LangGraph | Automatic |
| **Limiting concurrency** | **YOU** | **Semaphore** |
| **Resource control** | **YOU** | **Semaphore** |

### The Two-Layer System

```
┌─────────────────────────────────────────┐
│  LangGraph (Framework Level)            │
│  - Launches all Send() objects          │
│  - Manages async scheduling             │
│  - Aggregates state with reducers       │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Semaphore (Application Level)          │
│  - Limits to N concurrent (e.g., 4)    │
│  - Queues excess tasks                  │
│  - Releases slots as tasks complete     │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Lock (Critical Section Level)          │
│  - Serializes diff application (1 at a │
│    time)                                │
│  - Prevents git conflicts               │
└─────────────────────────────────────────┘
```

**All three are necessary!** ✅

---

## ❓ Question 3: Why Were Results Empty?

### The Problem
LangGraph was receiving multiple values for `completed_tasks` but didn't know how to merge them!

**Error:**
```
InvalidUpdateError: Can receive only one value per step. 
Use an Annotated key to handle multiple values.
```

### The Root Cause
```python
# ❌ BEFORE (No reducer)
class TaskState(TypedDict, total=False):
    completed_tasks: list[dict]  # No reducer!

# Task 1 returns: completed_tasks = [result1]
# Task 2 returns: completed_tasks = [result2]
# LangGraph: "Which one should I use?! ERROR!" 💥
```

### The Fix
```python
# ✅ AFTER (With reducer)
class TaskState(TypedDict, total=False):
    completed_tasks: Annotated[list[dict], add]  # Has reducer!

# Task 1 returns: completed_tasks = [result1]
# Task 2 returns: completed_tasks = [result2]
# LangGraph: "I'll concatenate them: [result1, result2]" ✅
```

---

## 🎓 Complete Example for Stomper

Here's how you'd apply this to Stomper:

```python
from operator import add
from typing import Annotated, TypedDict

class StomperState(TypedDict, total=False):
    # Session info (single values - no reducer needed)
    session_id: str
    project_root: Path
    
    # Parallel processing results (need reducers!)
    successful_fixes: Annotated[list[str], add]        # Concatenate
    failed_fixes: Annotated[list[str], add]            # Concatenate
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Sum
    
    # Detailed metrics (custom reducer)
    file_metrics: Annotated[
        list[dict], 
        lambda existing, new: existing + new  # Concatenate
    ]

class StomperWorkflow:
    def __init__(self, max_parallel_files: int = 4):
        # Concurrency control
        self._parallel_semaphore = asyncio.Semaphore(max_parallel_files)
        self._diff_lock = asyncio.Lock()
    
    def _fan_out_files(self, state: StomperState):
        """Fan out to parallel file processing."""
        return [
            Send("process_file_parallel", {
                **state,
                "current_file": file,
            })
            for file in state["files"]
        ]
    
    async def _process_file_parallel(self, state: dict) -> dict:
        """Process one file in parallel with concurrency control."""
        file = state["current_file"]
        
        # LAYER 1: Semaphore (limit active workers)
        async with self._parallel_semaphore:
            logger.info(f"Processing {file.file_path}")
            
            # Create worktree → Fix → Test
            worktree = create_worktree(file)
            
            try:
                fix_result = await fix_file(worktree, file)
                test_result = await test_file(worktree, file)
                diff = extract_diff(worktree)
                
                # LAYER 2: Lock (serialize critical section)
                async with self._diff_lock:
                    apply_to_main(diff)
                    commit_in_main(file)
                
                return {
                    "successful_fixes": [str(file.file_path)],  # ← Aggregated!
                    "total_errors_fixed": len(fix_result.fixed),  # ← Summed!
                    "file_metrics": [{                           # ← Concatenated!
                        "file": str(file.file_path),
                        "time": fix_result.elapsed,
                        "errors_fixed": len(fix_result.fixed),
                    }],
                }
                
            finally:
                destroy_worktree(worktree)
```

---

## 🔍 Observing Aggregation in Action

Run the demo and watch:

```bash
uv run python demo_langgraph_parallel.py 10 3
```

**What you'll see:**
```
>> Parallel Processing Summary
Completed: 10              ← All 10 results aggregated! ✅
Failed: 0
Total time: 8.15s

>> Task Metrics (Aggregated)
Average task time: 2.62s   ← Calculated from ALL tasks
Fastest task: 1.51s        ← Found across ALL tasks
Slowest task: 4.03s        ← Found across ALL tasks
```

**This proves aggregation works!** The `_finalize` node receives ALL the results merged together by LangGraph.

---

## 💡 Key Takeaways

### 1. **Aggregation Answer**
Use `Annotated[list, add]` to tell LangGraph how to merge parallel results:
```python
successful_fixes: Annotated[list[str], add]  # Auto-concatenates!
```

### 2. **Semaphore Answer**  
LangGraph doesn't limit concurrency - you MUST use semaphore:
```python
self._semaphore = asyncio.Semaphore(4)  # Your resource control
```

### 3. **Empty Results Answer**
Results were empty because no reducer was defined. LangGraph couldn't merge them!

---

## 🚀 What This Means for Stomper

You'll need **all three** pieces:

1. **LangGraph's Send()** - Parallel execution framework ✅
2. **Semaphore** - Limit max concurrent files (YOUR control) ✅
3. **Lock** - Serialize diff application (already have it!) ✅
4. **Annotated reducers** - Aggregate results (easy to add!) ✅

**Perfect combination of framework power + application control!** 🌟

---

## 📚 Resources

- **Demo**: `demo_langgraph_parallel.py` - Working example with all 3 pieces
- **README**: `demo_langgraph_parallel_README.md` - How to run it
- **This FAQ**: Answers to your exact questions

Try the demo with different concurrency levels to see it all work! 🎉

