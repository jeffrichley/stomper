#!/usr/bin/env env python
"""Demo: LangGraph Parallel Processing with Concurrency Limits

This demonstrates:
1. LangGraph's Send API for parallel execution
2. Semaphore-based concurrency limiting
3. Serialized critical sections (like our diff application)
4. Result aggregation

Run with: uv run python demo_langgraph_parallel.py
"""

import asyncio
import logging
import time
from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Send
from rich.console import Console
from rich.logging import RichHandler

# Setup rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger(__name__)
console = Console()


# ==================== State Definition ====================

class TaskState(TypedDict, total=False):
    """State for our demo workflow.
    
    KEY CONCEPT: Annotated with Reducers
    =====================================
    When multiple parallel branches return the same state key,
    LangGraph needs to know HOW to merge them.
    
    Annotated[type, reducer] tells LangGraph:
    - 'add' reducer = concatenate lists (built-in from operator module)
    - Custom lambda = define your own merge logic
    
    Without Annotated: ERROR! "Can receive only one value per step"
    With Annotated: Automatic aggregation! ✅
    """
    # Input
    task_ids: list[int]
    max_concurrent: int
    
    # Current task being processed (for parallel nodes)
    current_task_id: int | None
    
    # AGGREGATED RESULTS (using reducers)
    # Each parallel branch returns a list with 1 item
    # LangGraph concatenates all of them together
    completed_tasks: Annotated[list[dict[str, Any]], add]  # [task1] + [task2] + [task3]
    failed_tasks: Annotated[list[int], add]                 # [1] + [3] + [5]
    
    total_processing_time: float


# ==================== Demo Workflow ====================

class ParallelWorkflowDemo:
    """Demonstrates LangGraph parallel processing with concurrency control.
    
    THREE LAYERS OF CONTROL:
    ========================
    1. LangGraph (Framework): Launches all Send() in parallel
    2. Semaphore (Concurrency): Limits to max N concurrent
    3. Lock (Critical Section): Serializes specific operations
    """
    
    def __init__(self, max_concurrent: int = 3):
        """Initialize demo workflow.
        
        Args:
            max_concurrent: Maximum tasks to process concurrently
        """
        self.max_concurrent = max_concurrent
        
        # LAYER 1: Concurrency control (limit active tasks)
        # Without this, LangGraph would run ALL tasks at once! 💥
        self._concurrency_semaphore = asyncio.Semaphore(max_concurrent)
        
        # LAYER 2: Critical section lock (serialize specific operations)
        # Like our diff application - only ONE at a time!
        self._critical_section_lock = asyncio.Lock()
        
        # Metrics
        self._critical_section_count = 0
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Any:
        """Build LangGraph state machine with parallel processing.
        
        Key: We use Annotated[list, add] in TaskState to tell LangGraph
        how to merge results from parallel branches automatically!
        """
        workflow = StateGraph(TaskState)
        
        # Nodes
        workflow.add_node("initialize", self._initialize)
        workflow.add_node("process_task", self._process_single_task)  # Runs in parallel!
        workflow.add_node("finalize", self._finalize)
        
        # Edges
        workflow.set_entry_point("initialize")
        
        # After initialize, fan out to parallel processing
        workflow.add_conditional_edges(
            "initialize",
            self._fan_out_tasks,
            # LangGraph will execute all Send() objects in parallel!
        )
        
        # After ALL parallel tasks complete, go to finalize
        # (LangGraph automatically waits for all parallel branches)
        workflow.add_edge("process_task", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    # ==================== Nodes ====================
    
    async def _initialize(self, state: TaskState) -> TaskState:
        """Initialize the workflow."""
        task_ids = state.get("task_ids", list(range(1, 11)))  # Default: 10 tasks
        
        console.print("\n[bold cyan]>> Starting Parallel Processing Demo[/bold cyan]")
        console.print(f"[cyan]Tasks to process: {task_ids}[/cyan]")
        console.print(f"[cyan]Max concurrent: {self.max_concurrent}[/cyan]\n")
        
        return {
            **state,
            "task_ids": task_ids,
            "max_concurrent": self.max_concurrent,
            "completed_tasks": [],
            "failed_tasks": [],
            "total_processing_time": time.time(),
        }
    
    def _fan_out_tasks(self, state: TaskState):
        """Fan out: Send each task to parallel processor.
        
        CRITICAL: This returns a list of Send() objects.
        LangGraph will:
        1. Launch ALL of them into the async event loop
        2. BUT: Our semaphore in _process_single_task limits actual concurrency
        
        Think of it as:
        - LangGraph: "Here are 100 tasks to do in parallel!"
        - Semaphore: "OK but only 4 can actually run at once"
        """
        task_ids = state["task_ids"]
        
        if not task_ids:
            return "finalize"  # No tasks, skip to end
        
        # Create a Send for each task
        # NOTE: All will be scheduled, but semaphore controls active count
        return [
            Send("process_task", {
                **state,
                "current_task_id": task_id,
            })
            for task_id in task_ids
        ]
    
    async def _process_single_task(self, state: dict) -> dict:
        """Process a single task in parallel (with concurrency control).
        
        This method is called by LangGraph for EACH Send() object.
        Multiple instances run concurrently, but:
        - Semaphore limits to max_concurrent active instances
        - Lock serializes the critical section
        
        ANSWER TO Q2: Why semaphore if LangGraph can handle it?
        Because LangGraph CANNOT limit concurrency - it launches all
        Send() objects immediately. The semaphore is YOUR control!
        """
        task_id = state["current_task_id"]
        
        # CONCURRENCY CONTROL: Acquire semaphore (waits if limit reached)
        # This is THE answer to Q2 - without this, all tasks run at once!
        async with self._concurrency_semaphore:
            # Show current concurrency
            active_count = self.max_concurrent - self._concurrency_semaphore._value
            logger.info(
                f"[bold green]>> [{active_count}/{self.max_concurrent}][/bold green] "
                f"Started processing Task {task_id}"
            )
            
            start_time = time.time()
            
            try:
                # Simulate processing work (each task takes 1-3 seconds)
                processing_time = 1 + (task_id % 3)  # Vary the time
                await asyncio.sleep(processing_time)
                
                # CRITICAL SECTION: Simulate something that must be serialized
                # (Like our diff application - only one at a time!)
                async with self._critical_section_lock:
                    self._critical_section_count += 1
                    logger.info(
                        f"[yellow]LOCK: Task {task_id} entered critical section "
                        f"(#{self._critical_section_count})[/yellow]"
                    )
                    
                    # Simulate critical work (like applying a diff)
                    await asyncio.sleep(0.5)
                    
                    logger.info(
                        f"[yellow]UNLOCK: Task {task_id} exited critical section[/yellow]"
                    )
                
                # Success!
                elapsed = time.time() - start_time
                logger.info(
                    f"[bold green]DONE: Task {task_id} completed "
                    f"({elapsed:.1f}s)[/bold green]"
                )
                
                # ANSWER TO Q1 & Q3: How to aggregate information?
                # Return a list with ONE item - LangGraph will concatenate
                # all of them using the 'add' reducer!
                result = {
                    "success": True,
                    "task_id": task_id,
                    "processing_time": elapsed,
                    "result": f"Result from task {task_id}",
                }
                
                return {
                    # This list gets concatenated with all other parallel results
                    "completed_tasks": [result],  # [task1] + [task2] + [task3] = merged!
                }
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"[bold red]ERROR: Task {task_id} failed: {e} "
                    f"({elapsed:.1f}s)[/bold red]"
                )
                
                # Return failure - LangGraph will accumulate using 'add' reducer
                return {
                    "failed_tasks": [task_id],  # Add reducer will append this
                }
    
    
    async def _finalize(self, state: TaskState) -> TaskState:
        """Finalize workflow and show summary with aggregated metrics."""
        total_time = time.time() - state["total_processing_time"]
        
        completed_tasks = state.get("completed_tasks", [])
        failed_tasks = state.get("failed_tasks", [])
        
        completed_count = len(completed_tasks)
        failed_count = len(failed_tasks)
        
        console.print("\n[bold cyan]>> Parallel Processing Summary[/bold cyan]")
        console.print(f"[green]Completed: {completed_count}[/green]")
        console.print(f"[red]Failed: {failed_count}[/red]")
        console.print(f"[cyan]Total time: {total_time:.2f}s[/cyan]")
        console.print(f"[yellow]Critical section entries: {self._critical_section_count}[/yellow]")
        
        # Show aggregated metrics from completed tasks
        if completed_count > 0:
            avg_task_time = sum(t["processing_time"] for t in completed_tasks) / completed_count
            min_task_time = min(t["processing_time"] for t in completed_tasks)
            max_task_time = max(t["processing_time"] for t in completed_tasks)
            
            console.print(f"\n[bold cyan]>> Task Metrics (Aggregated)[/bold cyan]")
            console.print(f"[cyan]Average task time: {avg_task_time:.2f}s[/cyan]")
            console.print(f"[cyan]Fastest task: {min_task_time:.2f}s[/cyan]")
            console.print(f"[cyan]Slowest task: {max_task_time:.2f}s[/cyan]")
            
            sequential_time = avg_task_time * (completed_count + failed_count)
            speedup = sequential_time / total_time if total_time > 0 else 1
            
            console.print(f"\n[bold magenta]>> Speedup Analysis[/bold magenta]")
            console.print(f"[cyan]Sequential would take: {sequential_time:.2f}s[/cyan]")
            console.print(f"[green]Parallel took: {total_time:.2f}s[/green]")
            console.print(f"[bold yellow]Speedup: {speedup:.2f}x[/bold yellow]")
        
        return state


# ==================== Main Demo ====================

async def run_demo(num_tasks: int = 10, max_concurrent: int = 3):
    """Run the parallel processing demo.
    
    Args:
        num_tasks: Number of tasks to process
        max_concurrent: Maximum concurrent tasks
    """
    # Create workflow
    workflow = ParallelWorkflowDemo(max_concurrent=max_concurrent)
    
    # Initial state
    initial_state: TaskState = {
        "task_ids": list(range(1, num_tasks + 1)),
        "max_concurrent": max_concurrent,
    }
    
    # Run workflow
    console.print(f"\n[bold]Running demo with {num_tasks} tasks, max {max_concurrent} concurrent[/bold]\n")
    
    final_state = await workflow.graph.ainvoke(initial_state)
    
    return final_state


async def demo_comparison():
    """Run comparison: sequential vs different concurrency levels."""
    console.print("\n[bold magenta]>> Concurrency Comparison Demo[/bold magenta]\n")
    
    num_tasks = 10
    
    # Run with different concurrency levels
    configs = [
        (1, "Sequential (no parallelism)"),
        (2, "Low concurrency"),
        (3, "Medium concurrency"),
        (5, "High concurrency"),
    ]
    
    for max_concurrent, description in configs:
        console.print(f"\n[bold cyan]>>> {description} (max_concurrent={max_concurrent})[/bold cyan]")
        await run_demo(num_tasks=num_tasks, max_concurrent=max_concurrent)
        await asyncio.sleep(1)  # Brief pause between runs


if __name__ == "__main__":
    import sys
    
    console.print("""
[bold cyan]================================================================
  LangGraph Parallel Processing Demo                         
                                                              
  This demo shows:                                            
  - LangGraph's Send API for parallel execution              
  - Semaphore-based concurrency limiting                     
  - Serialized critical sections (with lock)                 
  - Result aggregation                                        
================================================================[/bold cyan]
    """)
    
    # Choose demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        # Run comparison
        asyncio.run(demo_comparison())
    else:
        # Run single demo
        num_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        max_concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        
        asyncio.run(run_demo(num_tasks=num_tasks, max_concurrent=max_concurrent))
    
    console.print("\n[bold green]>> Demo complete![/bold green]\n")

