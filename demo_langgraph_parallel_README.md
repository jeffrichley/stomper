# LangGraph Parallel Processing Demo 🚀

A clean demonstration of LangGraph's parallel processing capabilities with concurrency control.

## 🎯 What This Demonstrates

1. **LangGraph's Send API** - How to fan out work to parallel nodes
2. **Semaphore Concurrency Control** - Limit max concurrent tasks (like `max_parallel_files`)
3. **Serialized Critical Sections** - Lock for operations that must be sequential (like our diff application)
4. **Result Aggregation** - How LangGraph collects results from parallel branches
5. **Performance Analysis** - See the actual speedup from parallelization

## 🚀 Running the Demo

### Basic Demo (10 tasks, max 3 concurrent)
```bash
uv run python demo_langgraph_parallel.py
```

### Custom Parameters
```bash
# 20 tasks, max 5 concurrent
uv run python demo_langgraph_parallel.py 20 5

# 15 tasks, max 2 concurrent
uv run python demo_langgraph_parallel.py 15 2
```

### Comparison Mode (see different concurrency levels)
```bash
uv run python demo_langgraph_parallel.py compare
```

## 📊 What You'll See

### During Execution:
```
🔄 [2/3] Started processing Task 5
🔒 Task 5 entered critical section (#3)
🔓 Task 5 exited critical section
✅ Task 5 completed (1.7s)
```

- `[2/3]` = 2 tasks currently running out of max 3
- `🔒` = Entered the serialized section (only one at a time!)
- `🔓` = Exited the serialized section
- Time shows how long each task took

### Summary:
```
📊 Parallel Processing Summary
✅ Completed: 10
❌ Failed: 0
⏱️  Total time: 8.5s
🔒 Critical section entries: 10

🚀 Speedup Analysis
Sequential would take: 20.0s
Parallel took: 8.5s
Speedup: 2.35x
```

## 🔑 Key Concepts Demonstrated

### 1. Fan-Out Pattern
```python
def _fan_out_tasks(self, state):
    """LangGraph executes all Send() objects in parallel!"""
    return [
        Send("process_task", {"current_task_id": task_id})
        for task_id in task_ids
    ]
```

### 2. Concurrency Control
```python
async with self._concurrency_semaphore:
    # Only N tasks can be here at once
    # Others wait in queue
    await process_task()
```

### 3. Critical Section (Serialization)
```python
async with self._critical_section_lock:
    # Only ONE task can be here at a time
    # Like our diff application to main workspace
    await apply_diff_to_main()
```

## 📈 Expected Behavior

### With max_concurrent=1 (Sequential)
- Tasks run one at a time
- No speedup
- Safest but slowest

### With max_concurrent=3 (Good Balance)
- Up to 3 tasks run simultaneously
- ~2-3x speedup (depending on task variance)
- Good resource usage

### With max_concurrent=10 (Aggressive)
- All tasks run simultaneously
- Max speedup but high resource usage
- Critical section becomes bottleneck

## 🎓 Learning Points

1. **Semaphore = "Max N at once"**
   - Controls how many tasks can run concurrently
   - Like `max_parallel_files` in Stomper

2. **Lock = "Only 1 at a time"**
   - Ensures critical operations are serialized
   - Like diff application in Stomper

3. **LangGraph handles the complexity**
   - Automatic task scheduling
   - Result aggregation
   - State management

4. **Watch the logs!**
   - See tasks starting/stopping
   - See when tasks wait for a slot
   - See critical section serialization

## 🔄 How This Maps to Stomper

| Demo Concept | Stomper Equivalent |
|--------------|-------------------|
| `process_task` | Process one file (create worktree → fix → test → destroy) |
| `_concurrency_semaphore` | Limit max concurrent files being fixed |
| `_critical_section_lock` | Diff application to main workspace (must be serial) |
| `task_id` | File path being processed |
| `Send()` | Fan out to multiple files |

## 💡 Try These Experiments

1. **See the semaphore in action:**
   ```bash
   # 10 tasks, only 2 concurrent - watch them queue!
   uv run python demo_langgraph_parallel.py 10 2
   ```

2. **Compare speedup:**
   ```bash
   # Run comparison mode
   uv run python demo_langgraph_parallel.py compare
   ```

3. **Stress test:**
   ```bash
   # 50 tasks, 8 concurrent
   uv run python demo_langgraph_parallel.py 50 8
   ```

## 🎯 Next Steps

After understanding this demo:
1. Apply the same pattern to Stomper's file processing
2. Replace `process_task` with `process_single_file_parallel`
3. Keep the semaphore and lock concepts
4. Enjoy parallel file fixing! 🚀

## 🐛 What to Watch For

- **Lock contention** - If critical section is slow, it becomes bottleneck
- **Semaphore tuning** - Too high = resource issues, too low = slow
- **Task variance** - Some tasks take longer, affecting overall speedup
- **Error handling** - Failed tasks shouldn't break others

---

**This is the exact pattern we'll use in Stomper!** 🌟

