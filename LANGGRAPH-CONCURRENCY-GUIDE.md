# LangGraph Concurrency Control - Complete Guide 🎯

## 🎉 **YOU WERE RIGHT!**

LangGraph **DOES** have built-in concurrency limiting via `max_concurrency` config parameter!

Source: [LangGraph _executor.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/_executor.py)

---

## 📚 **Two Approaches to Concurrency Control**

### **Option 1: LangGraph's Built-in (RECOMMENDED)**

```python
# Set max_concurrency in config when invoking graph
config = {"max_concurrency": 4}
final_state = await graph.ainvoke(initial_state, config=config)
```

**How it works internally:**
```python
# From LangGraph source code (_executor.py):
if max_concurrency := config.get("max_concurrency"):
    self.semaphore = asyncio.Semaphore(max_concurrency)
    
# When submitting tasks:
if self.semaphore:
    coro = gated(self.semaphore, coro)  # Wraps in semaphore!

async def gated(semaphore, coro):
    async with semaphore:
        return await coro
```

**Pros:**
- ✅ Framework-managed (tested, robust)
- ✅ Simple - just set config parameter
- ✅ Applies to ALL parallel operations automatically
- ✅ Less code to maintain
- ✅ Works with LangSmith observability

**Cons:**
- ⚠️ Global limit (applies to everything)
- ⚠️ Less granular control

---

### **Option 2: Manual Semaphore (MORE CONTROL)**

```python
class Workflow:
    def __init__(self, max_parallel: int = 4):
        self._semaphore = asyncio.Semaphore(max_parallel)
    
    async def process(self, state):
        async with self._semaphore:
            # Your code here
            ...
```

**Pros:**
- ✅ Granular control per operation
- ✅ Different limits for different things
- ✅ Explicit and visible in code

**Cons:**
- ⚠️ More boilerplate
- ⚠️ You manage lifecycle
- ⚠️ Could conflict with LangGraph's built-in

---

## 🎯 **When to Use Which?**

### Use **Built-in** (`max_concurrency` config) When:
- ✅ You want simple, global concurrency limiting
- ✅ Same limit applies to all parallel operations
- ✅ You trust the framework to handle it
- ✅ **This covers 90% of use cases!**

### Use **Manual Semaphore** When:
- ✅ Need different limits for different operations
- ✅ Want explicit control in code
- ✅ Complex resource management scenarios
- ✅ Need to observe semaphore state directly

### Use **BOTH** When:
- ⚠️ Generally **DON'T** - they could conflict!
- ⚠️ Unless you have very specific needs

---

## 🚀 **Recommended Approach for Stomper**

### **Use LangGraph's Built-in!**

```python
class StomperWorkflow:
    def __init__(self, project_root: Path, max_parallel_files: int = 4):
        self.max_parallel_files = max_parallel_files
        
        # ONLY need lock for critical section (diff application)
        self._diff_application_lock = asyncio.Lock()
        
        # NO semaphore needed! LangGraph handles it
        
        self.graph = self._build_graph()
    
    async def run(self, config: dict[str, Any]) -> StomperState:
        """Run workflow with concurrency control."""
        
        initial_state = {...}
        
        # Set max_concurrency in config
        run_config = {
            "max_concurrency": self.max_parallel_files,  # ← LangGraph handles!
            "recursion_limit": 100,
        }
        
        return await self.graph.ainvoke(initial_state, config=run_config)
    
    async def _process_single_file_parallel(self, state: dict) -> dict:
        """Process one file - LangGraph limits concurrency automatically!"""
        file = state["current_file"]
        
        # NO semaphore needed here - LangGraph controls concurrency!
        logger.info(f"Processing {file.file_path}")
        
        worktree = create_worktree(file)
        
        try:
            fix_file(worktree)
            test_file(worktree)
            diff = extract_diff(worktree)
            
            # LOCK still needed for critical section!
            async with self._diff_application_lock:
                apply_to_main(diff)
                commit_in_main(file)
            
            return {"successful_fixes": [str(file.file_path)]}
            
        finally:
            destroy_worktree(worktree)
```

---

## 📊 **How Both Layers Work Together**

Even with `max_concurrency`, you still need the **lock** for critical sections:

```
LangGraph's max_concurrency (Framework)
    ↓
    Limits to N concurrent file processing tasks
    ↓
Your Lock (Application)
    ↓
    Serializes diff application (only 1 at a time)
```

**Example with max_concurrency=4:**
- 4 files process in parallel ✅
- Each file: create worktree → fix → test (in parallel)
- Diff application: **One at a time** (lock ensures this) 🔒
- After diff applied: next file immediately starts (slot freed)

---

## 🔬 **Proof from Source Code**

From [`_executor.py` lines 131-140](https://github.com/langchain-ai/langgraph/blob/420550501f8a28d02da3d16f1ad9fa7f23cd9063/libs/langgraph/langgraph/pregel/_executor.py#L131-L140):

```python
class AsyncBackgroundExecutor:
    def __init__(self, config: RunnableConfig) -> None:
        self.tasks: dict[asyncio.Future, tuple[bool, bool]] = {}
        self.sentinel = object()
        self.loop = asyncio.get_running_loop()
        
        # HERE IT IS! 🎯
        if max_concurrency := config.get("max_concurrency"):
            self.semaphore: asyncio.Semaphore | None = asyncio.Semaphore(
                max_concurrency
            )
        else:
            self.semaphore = None
```

From [`_executor.py` lines 152-154](https://github.com/langchain-ai/langgraph/blob/420550501f8a28d02da3d16f1ad9fa7f23cd9063/libs/langgraph/langgraph/pregel/_executor.py#L152-L154):

```python
def submit(self, fn, *args, **kwargs):
    coro = fn(*args, **kwargs)
    if self.semaphore:
        coro = gated(self.semaphore, coro)  # Wraps in semaphore!
```

From [`_executor.py` lines 214-217](https://github.com/langchain-ai/langgraph/blob/420550501f8a28d02da3d16f1ad9fa7f23cd9063/libs/langgraph/langgraph/pregel/_executor.py#L214-L217):

```python
async def gated(semaphore: asyncio.Semaphore, coro):
    """A coroutine that waits for a semaphore before running another coroutine."""
    async with semaphore:
        return await coro
```

**LangGraph uses a semaphore internally when you set `max_concurrency`!** ✅

---

## ✅ **Updated Recommendations**

### For Stomper (Parallel File Processing)

**SIMPLEST APPROACH:**
```python
class StomperWorkflow:
    def __init__(self, max_parallel_files: int = 4):
        # Just the lock - no semaphore needed!
        self._diff_lock = asyncio.Lock()
    
    async def run(self, config):
        return await self.graph.ainvoke(
            initial_state,
            config={"max_concurrency": self.max_parallel_files}  # ← Magic!
        )
```

**Still need the lock for diff application!** (LangGraph can't know which operations need serialization)

---

## 🎓 **Key Learnings**

1. **LangGraph HAS built-in concurrency limiting** ✅
   - Set via `config={"max_concurrency": N}`
   - Uses semaphore internally
   - Undocumented in main docs but exists in code!

2. **Locks are still necessary** 🔒
   - For operations that MUST be serial (diff application)
   - LangGraph can't know your business logic

3. **Choose based on needs:**
   - Simple global limit → Use `max_concurrency` config ✅
   - Different limits for different operations → Manual semaphore
   - Critical sections → Always use locks 🔒

---

## 📝 **Final Recommendation for Stomper**

```python
# RECOMMENDED: Use LangGraph's built-in
config = {
    "max_concurrency": 4,  # Limit file processing
    "recursion_limit": 100,
}

final_state = await workflow.graph.ainvoke(initial_state, config=config)
```

**Rationale:**
- Simpler code
- Framework-managed
- Same behavior as manual semaphore
- One less thing to maintain
- **Still use lock for diff application!**

---

## 🎊 **Summary**

**You were absolutely right!** 🎯

LangGraph has built-in `max_concurrency` support:
- Discovered in source code: `_executor.py`
- Uses semaphore internally
- Set via config parameter
- Works exactly like manual approach

**For Stomper:**
- ✅ Use `config={"max_concurrency": N}`
- ✅ Keep the diff application lock
- ✅ Remove manual semaphore
- ✅ Simpler and cleaner!

**Demos:**
- `demo_langgraph_builtin_concurrency.py` - Built-in approach ← **Use this!**
- `demo_langgraph_parallel.py` - Manual approach (educational)

Thank you for finding this! 🙏 The built-in approach is definitely the way to go!

