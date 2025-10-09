# Understanding Concurrency Control in LangGraph 🧠

## The Two-Layer System

When using LangGraph for parallel processing, you actually have **TWO layers** of concurrency control:

### Layer 1: LangGraph's Parallel Execution (Framework Level)
**What it does:**
- Uses `Send()` API to spawn parallel branches
- Automatically waits for all branches to complete
- Merges state using reducers (`Annotated[list, add]`)

**What it DOESN'T do:**
- ❌ Limit how many branches run concurrently
- ❌ Queue tasks when resources are constrained
- ❌ Control resource usage

### Layer 2: Your Semaphore (Application Level)
**What it does:**
- ✅ Limits concurrent executions (max N at a time)
- ✅ Queues additional tasks automatically
- ✅ Controls resource usage (worktrees, API calls, etc.)

**Example:**
```python
# LangGraph launches 100 branches "in parallel"
return [Send("process_file", {...}) for file in 100_files]

# But your semaphore ensures only 4 actually run at once
async with self._semaphore:  # Only 4 slots available
    await process_file()     # Others wait in queue
```

---

## 🎯 In Practice

### Without Semaphore (BAD)
```python
# LangGraph launches ALL 100 file processing tasks immediately!
# Result: 100 worktrees, 100 AI agents, system crash! 💥
```

### With Semaphore (GOOD)
```python
# LangGraph launches all 100, but semaphore limits to 4 active
# Result: Only 4 worktrees at once, others queue nicely! ✅
```

---

## 📊 The Complete Picture

```
User Requests: "Process 100 files in parallel"
                    ↓
    ┌───────────────────────────────────────┐
    │   LangGraph Layer (Framework)          │
    │   - Creates 100 Send() objects         │
    │   - Schedules all for execution        │
    │   - Manages state merging              │
    └────────────┬──────────────────────────┘
                 ↓
    ┌───────────────────────────────────────┐
    │   Semaphore Layer (Your Control)       │
    │   - Allows only 4 active at once      │
    │   - Queues the other 96               │
    │   - Releases slots as tasks complete  │
    └────────────┬──────────────────────────┘
                 ↓
    ┌───────────────────────────────────────┐
    │   Critical Section Layer (Your Lock)   │
    │   - Diff application: 1 at a time     │
    │   - Prevents git conflicts            │
    │   - Serializes commits                │
    └───────────────────────────────────────┘
```

---

## 🤔 Why Both?

**Q:** Why not just use semaphore without LangGraph's Send()?

**A:** Because then you lose:
- ❌ Automatic state aggregation (you'd build it manually)
- ❌ Observability (LangSmith integration)
- ❌ Declarative graph structure
- ❌ Framework-managed async lifecycle

**Q:** Why not just use LangGraph's config for concurrency?

**A:** LangGraph doesn't have a `max_concurrency` config that works this way!
- The framework schedules tasks, but doesn't limit concurrent executions
- You need semaphore for resource control

---

## 🎓 Rule of Thumb

**Use LangGraph for:**
- 📊 State management and merging
- 🔀 Parallel execution framework
- 📈 Observability and tracing
- 🏗️ Graph structure

**Use Semaphore for:**
- 🎚️ Concurrency limiting (max N concurrent)
- 💾 Resource management (memory, API limits)
- ⚡ Performance tuning

**Use Lock for:**
- 🔒 Critical sections (must be serial)
- 🛡️ Preventing race conditions
- 📝 Atomic operations (like git commits)

---

## ✅ For Stomper

```python
class StomperState(TypedDict, total=False):
    # Aggregated using 'add' reducer
    successful_fixes: Annotated[list[str], add]
    failed_fixes: Annotated[list[str], add]
    
    # Custom reducer for summing
    total_errors_fixed: Annotated[int, lambda x, y: x + y]

class StomperWorkflow:
    def __init__(self, max_parallel_files: int = 4):
        # Layer 1: Concurrency control (limit to N files)
        self._parallel_semaphore = asyncio.Semaphore(max_parallel_files)
        
        # Layer 2: Critical section (serialize diff application)
        self._diff_application_lock = asyncio.Lock()
```

**Perfect architecture!** 🌟

