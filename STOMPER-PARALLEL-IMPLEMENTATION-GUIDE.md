# Stomper Parallel Processing - Complete Implementation Guide 🚀

## 🎯 **The Complete Pattern (Using LangGraph's Built-in Features)**

Based on your findings, here's the **BEST** way to implement parallel file processing in Stomper:

---

## ✅ **Three LangGraph Features to Use**

### 1. **`config={'max_concurrency': N}`** - Limit parallel tasks
- Built into LangGraph's executor
- No manual semaphore needed!
- [Source code](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/_executor.py)

### 2. **`Annotated[list, add]`** - Automatic result aggregation
- LangGraph merges results from parallel branches
- No manual collection needed!

### 3. **`defer=True`** - Wait for all branches before aggregating
- Ensures aggregation node runs AFTER all parallel tasks complete
- Perfect for fan-in operations

---

## 📝 **Complete Implementation for Stomper**

```python
from operator import add
from typing import Annotated
import asyncio
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


# ==================== State with Reducers ====================

class StomperState(TypedDict, total=False):
    # Session info
    session_id: str
    project_root: Path
    
    # File queue (input)
    files: list[FileState]
    
    # Current file (for parallel processing)
    current_file: FileState | None
    
    # AGGREGATED RESULTS (automatic merge with reducers!)
    successful_fixes: Annotated[list[str], add]  # Auto-concatenate
    failed_fixes: Annotated[list[str], add]      # Auto-concatenate
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Auto-sum
    
    # Metrics (aggregated)
    file_metrics: Annotated[list[dict], add]  # Auto-concatenate
    
    # Components
    mapper: object
    agent_manager: object
    prompt_generator: object


# ==================== Workflow Implementation ====================

class StomperWorkflowParallel:
    """Stomper workflow with parallel file processing."""
    
    def __init__(
        self,
        project_root: Path,
        max_parallel_files: int = 4,  # ← Configurable concurrency
        use_sandbox: bool = True,
        run_tests: bool = True,
    ):
        self.project_root = Path(project_root)
        self.max_parallel_files = max_parallel_files
        self.use_sandbox = use_sandbox
        self.run_tests_enabled = run_tests
        
        # Initialize components
        self.mapper = ErrorMapper(project_root=project_root)
        self.agent_manager = AgentManager(project_root=project_root, mapper=self.mapper)
        self.prompt_generator = PromptGenerator(project_root=project_root, mapper=self.mapper)
        self.quality_manager = QualityToolManager()
        
        if use_sandbox:
            self.sandbox_manager = SandboxManager(project_root=project_root)
        else:
            self.sandbox_manager = None
        
        # ONLY need lock for critical section (diff application)
        # NO semaphore - LangGraph's max_concurrency handles it!
        self._diff_application_lock = asyncio.Lock()
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Any:
        """Build parallel-capable workflow graph."""
        workflow = StateGraph(StomperState)
        
        # Sequential initialization
        workflow.add_node("initialize", self._initialize_session)
        workflow.add_node("collect_errors", self._collect_all_errors)
        
        # Parallel file processing
        workflow.add_node("process_file", self._process_single_file_parallel)
        
        # IMPORTANT: defer=True waits for ALL parallel files to complete!
        workflow.add_node("aggregate_results", self._aggregate_all_results, defer=True)
        
        # Final cleanup
        workflow.add_node("cleanup", self._cleanup_session)
        
        # Edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "collect_errors")
        
        # Fan-out to parallel processing
        workflow.add_conditional_edges(
            "collect_errors",
            self._fan_out_files,
        )
        
        # Each file goes to aggregate (but aggregate waits due to defer=True)
        workflow.add_edge("process_file", "aggregate_results")
        
        # After ALL results aggregated, cleanup
        workflow.add_edge("aggregate_results", "cleanup")
        workflow.add_edge("cleanup", END)
        
        return workflow.compile()
    
    # ==================== Nodes ====================
    
    async def _initialize_session(self, state: StomperState) -> StomperState:
        """Initialize session (no worktree - those are created per file)."""
        session_id = f"stomper-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        logger.info(f"Initializing session: {session_id}")
        logger.info(f"Max parallel files: {self.max_parallel_files}")
        
        return {
            **state,
            "session_id": session_id,
            "successful_fixes": [],
            "failed_fixes": [],
            "total_errors_fixed": 0,
            "file_metrics": [],
        }
    
    async def _collect_all_errors(self, state: StomperState) -> StomperState:
        """Collect errors in MAIN workspace."""
        logger.info("Collecting errors from quality tools")
        
        # Run quality tools in main workspace
        all_errors = self.quality_manager.run_tools(
            target_path=state["project_root"],
            project_root=state["project_root"],
            enabled_tools=state.get("enabled_tools", ["ruff"]),
        )
        
        # Group by file
        files_with_errors = self._group_errors_by_file(all_errors)
        
        logger.info(f"Found {len(all_errors)} errors in {len(files_with_errors)} files")
        
        return {
            **state,
            "files": files_with_errors,
        }
    
    def _fan_out_files(self, state: StomperState):
        """Fan out to parallel file processing.
        
        LangGraph will execute all Send() objects in parallel,
        respecting max_concurrency from config!
        """
        files = state.get("files", [])
        
        if not files:
            logger.info("No files with errors")
            return "aggregate_results"
        
        logger.info(f"Fanning out to {len(files)} parallel workers")
        
        # Send each file to parallel processing
        return [
            Send("process_file", {
                **state,
                "current_file": file,
            })
            for file in files
        ]
    
    async def _process_single_file_parallel(self, state: dict) -> dict:
        """Process a single file in parallel.
        
        CONCURRENCY: LangGraph limits active count via max_concurrency
        ISOLATION: Each file gets its own worktree
        CRITICAL SECTION: Diff application is locked (serialized)
        """
        file = state["current_file"]
        session_id = state["session_id"]
        
        # NO SEMAPHORE NEEDED! max_concurrency handles it
        logger.info(f"Processing {file.file_path}")
        
        start_time = time.time()
        
        try:
            # 1. Create worktree (isolated per file)
            worktree_id = f"{session_id}_{file.file_path.stem}"
            worktree_path = None
            
            if self.use_sandbox and self.sandbox_manager:
                worktree_path = self.sandbox_manager.create_sandbox(
                    worktree_id, "HEAD"
                )
                logger.info(f"Created worktree: {worktree_path}")
            
            # 2. Generate prompt
            prompt = await self._generate_prompt_for_file(file, worktree_path)
            
            # 3. Call agent
            fixed_code = await self._call_agent_for_file(file, worktree_path, prompt)
            
            # 4. Verify fixes
            verification = await self._verify_fixes_for_file(file, worktree_path)
            
            # 5. Run tests (if enabled)
            if self.run_tests_enabled:
                test_result = await self._run_tests_for_file(file, worktree_path)
                if not test_result["passed"]:
                    raise Exception("Tests failed")
            
            # 6. Extract diff
            diff = None
            if worktree_path:
                worktree_repo = Repo(worktree_path)
                diff = worktree_repo.git.diff("HEAD")
            
            # 7. CRITICAL SECTION: Apply to main (MUST be serialized!)
            async with self._diff_application_lock:
                logger.info(f"[LOCKED] Applying diff for {file.file_path}")
                
                if diff:
                    # Apply patch to main workspace
                    main_repo = Repo(self.project_root)
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".patch", delete=False
                    ) as f:
                        f.write(diff)
                        patch_file = f.name
                    
                    try:
                        main_repo.git.apply(patch_file)
                        main_repo.index.add([str(file.file_path)])
                        main_repo.index.commit(
                            f"fix(quality): {file.file_path.name}"
                        )
                        logger.info(f"Committed {file.file_path}")
                    finally:
                        Path(patch_file).unlink(missing_ok=True)
                
                logger.info(f"[UNLOCKED] Diff applied for {file.file_path}")
            
            # 8. Cleanup worktree
            if worktree_path and self.sandbox_manager:
                self.sandbox_manager.cleanup_sandbox(worktree_id)
                logger.info(f"Destroyed worktree: {worktree_id}")
            
            elapsed = time.time() - start_time
            
            # Return results - Annotated reducers will merge automatically!
            return {
                "successful_fixes": [str(file.file_path)],  # Will be concatenated
                "total_errors_fixed": len(verification.get("fixed_errors", [])),  # Will be summed
                "file_metrics": [{  # Will be concatenated
                    "file": str(file.file_path),
                    "time": elapsed,
                    "errors_fixed": len(verification.get("fixed_errors", [])),
                }],
            }
            
        except Exception as e:
            logger.error(f"Failed {file.file_path}: {e}")
            
            # Cleanup on error
            if worktree_path and self.sandbox_manager:
                try:
                    self.sandbox_manager.cleanup_sandbox(worktree_id)
                except:
                    pass
            
            # Return failure - will be aggregated
            return {
                "failed_fixes": [str(file.file_path)],
            }
    
    async def _aggregate_all_results(self, state: StomperState) -> StomperState:
        """Aggregate results from ALL parallel file processing.
        
        CRITICAL: defer=True ensures this runs AFTER all files are processed!
        
        By the time we reach here, Annotated reducers have already merged:
        - successful_fixes = ["file1.py", "file2.py", ...]
        - total_errors_fixed = 5 + 3 + 7 + ... = 15
        - file_metrics = [{file1}, {file2}, ...]
        """
        successful = state.get("successful_fixes", [])
        failed = state.get("failed_fixes", [])
        total_fixed = state.get("total_errors_fixed", 0)
        
        logger.info(f"\n>>> AGGREGATION COMPLETE <<<")
        logger.info(f"  Successful: {len(successful)}")
        logger.info(f"  Failed: {len(failed)}")
        logger.info(f"  Total errors fixed: {total_fixed}")
        
        # Calculate session metrics
        metrics = state.get("file_metrics", [])
        if metrics:
            avg_time = sum(m["time"] for m in metrics) / len(metrics)
            logger.info(f"  Average time per file: {avg_time:.2f}s")
        
        return state
    
    async def _cleanup_session(self, state: StomperState) -> StomperState:
        """Final cleanup and save learning data."""
        logger.info("Final session cleanup")
        
        # Save mapper learning data
        if state.get("mapper"):
            state["mapper"].save()
        
        # Generate summary
        logger.info(
            f"Session complete:\n"
            f"  - Files fixed: {len(state['successful_fixes'])}\n"
            f"  - Files failed: {len(state['failed_fixes'])}\n"
            f"  - Total errors fixed: {state['total_errors_fixed']}"
        )
        
        return state
    
    # ==================== Run Method ====================
    
    async def run(self, config: dict[str, Any]) -> StomperState:
        """Run parallel workflow.
        
        KEY: Set max_concurrency in config - LangGraph handles the rest!
        """
        initial_state: StomperState = {
            "project_root": self.project_root,
            "enabled_tools": config.get("enabled_tools", ["ruff"]),
            # Attach components
            "mapper": self.mapper,
            "agent_manager": self.agent_manager,
            "prompt_generator": self.prompt_generator,
        }
        
        # THE MAGIC: Set max_concurrency in config!
        run_config = {
            "max_concurrency": self.max_parallel_files,  # ← LangGraph handles!
            "recursion_limit": 100,
        }
        
        logger.info(f"Starting Stomper parallel workflow")
        logger.info(f"Max concurrent files: {self.max_parallel_files}")
        
        final_state = await self.graph.ainvoke(initial_state, config=run_config)
        
        return final_state
```

---

## 🎯 **Key Points**

### What You Need:
1. ✅ **`max_concurrency` config** - LangGraph's built-in
2. ✅ **`Annotated` reducers** - For state aggregation
3. ✅ **`defer=True`** - On aggregate node
4. ✅ **`asyncio.Lock`** - For diff application only

### What You DON'T Need:
- ❌ Manual semaphore (LangGraph has it built-in)
- ❌ Manual result collection (Annotated does it)
- ❌ Explicit "wait for all" logic (defer=True does it)

---

## 📊 **Workflow Diagram**

```
initialize_session (sequential)
    ↓
collect_errors (sequential, in MAIN workspace)
    ↓
fan_out_files (conditional)
    ↓
┌────────────────────────────────────────────────────────┐
│  PARALLEL FILE PROCESSING                               │
│  (max_concurrency=4 - up to 4 files at once)           │
│                                                         │
│  File 1: create_worktree → fix → test → extract_diff  │
│           ↓                                             │
│           LOCK: apply_to_main → commit → destroy       │
│                                                         │
│  File 2: create_worktree → fix → test → extract_diff  │
│           ↓                                             │
│           LOCK: apply_to_main → commit → destroy       │
│                                                         │
│  File 3: ...                                            │
│  File 4: ...                                            │
│  (File 5 waits for a slot...)                          │
└────────────────────────────────────────────────────────┘
    ↓ (All files complete)
aggregate_results (defer=True - waits for ALL files!)
    ↓
cleanup_session (sequential)
    ↓
END
```

---

## 🔒 **Concurrency Control Layers**

### Layer 1: LangGraph's `max_concurrency`
```python
config = {"max_concurrency": 4}
# LangGraph creates semaphore internally
# Limits to 4 concurrent file processing tasks
```

### Layer 2: Your Critical Section Lock
```python
async with self._diff_application_lock:
    # Only ONE file can apply diff at a time
    apply_to_main(diff)
    commit_in_main(file)
```

**Both work together perfectly!** 🎯

---

## 📈 **Performance Characteristics**

### With `max_concurrency=4`:

**Timeline:**
```
t=0s:   Files 1,2,3,4 start processing (max reached)
t=5s:   File 1 finishes, File 5 starts (slot freed)
t=7s:   File 2 finishes, File 6 starts (slot freed)
...
t=30s:  All files done, aggregate_results runs (defer=True)
t=31s:  Cleanup, END
```

**Speedup:**
- Sequential: 40 seconds (8 files × 5s average)
- Parallel (max=4): ~12 seconds (2 batches × 5s + overhead)
- **Speedup: ~3.3x** 🚀

---

## 🎨 **Configuration**

Update your `WorkflowConfig`:

```python
class WorkflowConfig(BaseModel):
    # ... existing fields ...
    
    # Parallel processing settings
    max_parallel_files: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum files to process in parallel"
    )
    parallel_mode: bool = Field(
        default=False,
        description="Enable parallel file processing"
    )
```

**Usage:**
```python
# Sequential (current behavior)
workflow = StomperWorkflowParallel(
    project_root=Path("."),
    max_parallel_files=1,  # Sequential
)

# Parallel (4 files at once)
workflow = StomperWorkflowParallel(
    project_root=Path("."),
    max_parallel_files=4,  # 4 concurrent files
)
```

---

## ✅ **Migration from Current Per-File Worktree**

The beautiful thing: **Your current per-file worktree architecture is PERFECT for this!**

### Current (Sequential):
```python
for file in files:
    create_worktree → fix → test → extract → apply → commit → destroy
```

### New (Parallel):
```python
# Same logic, just wrapped in parallel execution!
# max_concurrency config does the rest!
```

**Minimal changes needed:**
1. Change state fields to use `Annotated[list, add]`
2. Add `defer=True` to aggregate node
3. Pass `config={"max_concurrency": N}` when invoking
4. Keep the diff lock (critical!)

---

## 🎓 **Summary**

### The COMPLETE Pattern (All 4 Features):

```python
# 1. State with Annotated reducers
class StomperState(TypedDict, total=False):
    successful_fixes: Annotated[list[str], add]  # Auto-merge
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Auto-sum

# 2. Aggregate node with defer=True
workflow.add_node("aggregate", aggregate_results, defer=True)

# 3. Critical section lock
async with self._diff_lock:
    apply_to_main()

# 4. max_concurrency config
config = {"max_concurrency": 4}
await graph.ainvoke(state, config=config)
```

**Result:**
- ✅ Parallel file processing (up to N at once)
- ✅ Automatic result aggregation
- ✅ Waits for all files before final aggregation
- ✅ Safe diff application (serialized)
- ✅ Clean, maintainable code

---

## 🚀 **Next Steps for Stomper**

1. Update `StomperState` to use `Annotated[list, add]` for results
2. Simplify workflow to use `Send()` for fan-out
3. Add `defer=True` to final aggregation node
4. Remove manual semaphore (if you added one)
5. Pass `max_concurrency` in config when running

**Your per-file worktree architecture + LangGraph's built-in features = Perfect parallel processing!** 🌟

---

## 📚 **Demos Created**

1. **`demo_langgraph_complete_pattern.py`** ← **USE THIS!** Complete best practices
2. **`demo_langgraph_builtin_concurrency.py`** - Shows max_concurrency
3. **`demo_langgraph_parallel.py`** - Educational (manual approach)

**Run:** `uv run python demo_langgraph_complete_pattern.py compare`

---

Thank you for finding the `defer=True` feature - this completes the picture! 🙏✨

