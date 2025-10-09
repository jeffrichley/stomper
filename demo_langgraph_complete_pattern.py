#!/usr/bin/env python
"""Demo: Complete LangGraph Parallel Pattern - BEST PRACTICES

This demonstrates the COMPLETE pattern using LangGraph's built-in features:
1. Built-in max_concurrency (no manual semaphore)
2. Annotated reducers for state aggregation
3. defer=True for fan-in aggregation nodes
4. Lock for critical sections

This is the RECOMMENDED pattern for Stomper!

Run with: uv run python demo_langgraph_complete_pattern.py
"""

import asyncio
import logging
import time
from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from rich.console import Console
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])
logger = logging.getLogger(__name__)
console = Console()


# ==================== State Definition ====================

class CompleteState(TypedDict, total=False):
    """State demonstrating complete best practices.
    
    KEY FEATURES:
    - Annotated reducers for automatic aggregation
    - Separate fields for different aggregation strategies
    """
    # Input
    task_ids: list[int]
    
    # Current task (for parallel processing)
    current_task_id: int | None
    
    # AGGREGATED RESULTS (using Annotated reducers)
    completed_tasks: Annotated[list[dict[str, Any]], add]  # Concatenate lists
    total_processing_time: Annotated[float, lambda x, y: x + y]  # Sum floats
    
    # Session info
    session_start: float


# ==================== Complete Workflow ====================

class CompleteParallelWorkflow:
    """Demonstrates COMPLETE best-practice pattern for parallel processing.
    
    USES:
    1. max_concurrency config (NO manual semaphore!)
    2. Annotated reducers (automatic state aggregation)
    3. defer=True (wait for all branches before aggregating)
    4. Lock (for critical sections)
    """
    
    def __init__(self):
        """Initialize workflow."""
        # ONLY need lock for critical sections
        # NO semaphore - LangGraph handles concurrency!
        self._critical_section_lock = asyncio.Lock()
        self._critical_count = 0
        
        # Concurrency tracking
        self._active_tasks = 0  # Current number of active tasks
        self._max_concurrent_reached = 0  # Peak concurrent tasks observed
        self._active_lock = asyncio.Lock()  # Lock for updating counters
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Any:
        """Build graph using best practices."""
        workflow = StateGraph(CompleteState)
        
        # Nodes
        workflow.add_node("initialize", self._initialize)
        workflow.add_node("process_task", self._process_single_task)  # Runs in parallel
        
        # CRITICAL: defer=True waits for ALL parallel branches to complete!
        workflow.add_node("aggregate", self._aggregate_results, defer=True)
        workflow.add_node("finalize", self._finalize)
        
        # Edges
        workflow.add_edge(START, "initialize")
        
        # Fan-out to parallel processing
        workflow.add_conditional_edges(
            "initialize",
            self._fan_out_tasks,
        )
        
        # Each parallel task goes to aggregate
        # But aggregate won't run until ALL tasks are done (defer=True)
        workflow.add_edge("process_task", "aggregate")
        
        # After aggregation, finalize
        workflow.add_edge("aggregate", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    # ==================== Nodes ====================
    
    async def _initialize(self, state: CompleteState) -> CompleteState:
        """Initialize workflow."""
        task_ids = state.get("task_ids", list(range(1, 9)))
        
        console.print("\n[bold cyan]>> Complete Pattern Demo[/bold cyan]")
        console.print("[cyan]Features:[/cyan]")
        console.print("[cyan]  - Built-in max_concurrency (no manual semaphore)[/cyan]")
        console.print("[cyan]  - Annotated reducers (auto aggregation)[/cyan]")
        console.print("[cyan]  - defer=True on aggregate node[/cyan]")
        console.print("[cyan]  - Lock for critical sections[/cyan]\n")
        
        return {
            **state,
            "task_ids": task_ids,
            "completed_tasks": [],
            "total_processing_time": 0.0,
            "session_start": time.time(),
        }
    
    def _fan_out_tasks(self, state: CompleteState):
        """Fan out to parallel processing."""
        task_ids = state["task_ids"]
        
        if not task_ids:
            return "finalize"
        
        # LangGraph will run these in parallel (respecting max_concurrency)
        return [
            Send("process_task", {**state, "current_task_id": task_id})
            for task_id in task_ids
        ]
    
    async def _process_single_task(self, state: dict) -> dict:
        """Process a single task in parallel.
        
        BEST PRACTICE DEMO:
        - No manual semaphore (LangGraph handles via max_concurrency)
        - Lock only for critical section
        - Returns partial results for aggregation
        - TRACKS actual concurrency to prove max_concurrency works!
        """
        task_id = state["current_task_id"]
        
        # INCREMENT active task counter
        async with self._active_lock:
            self._active_tasks += 1
            current_active = self._active_tasks
            
            # Track peak concurrency
            if self._active_tasks > self._max_concurrent_reached:
                self._max_concurrent_reached = self._active_tasks
            
            console.log(
                f"[bold green]STARTED Task {task_id} "
                f"(Active: {current_active}, Peak: {self._max_concurrent_reached})[/bold green]"
            )
        
        start = time.time()
        
        try:
            # Simulate work (variable time)
            work_time = 1 + (task_id % 3)
            await asyncio.sleep(work_time)
            
            # CRITICAL SECTION: Only one task here at a time
            async with self._critical_section_lock:
                self._critical_count += 1
                console.log(f"[yellow]LOCK: Task {task_id} (#{self._critical_count})[/yellow]")
                await asyncio.sleep(0.2)  # Simulate critical work
                console.log(f"[yellow]UNLOCK: Task {task_id}[/yellow]")
            
            elapsed = time.time() - start
            console.log(f"[green]COMPLETED Task {task_id} ({elapsed:.1f}s)[/green]")
            
            # Return results - Annotated reducer will aggregate automatically
            return {
                "completed_tasks": [{
                    "task_id": task_id,
                    "processing_time": elapsed,
                }],
                "total_processing_time": elapsed,  # Will be summed via custom reducer
            }
        
        finally:
            # DECREMENT active task counter
            async with self._active_lock:
                self._active_tasks -= 1
                current_active = self._active_tasks
                console.log(
                    f"[cyan]Task {task_id} finished "
                    f"(Active now: {current_active})[/cyan]"
                )
    
    async def _aggregate_results(self, state: CompleteState) -> CompleteState:
        """Aggregate results from ALL parallel branches.
        
        CRITICAL: This node has defer=True, so it waits until ALL
        parallel tasks complete before running!
        
        By the time we reach here, all results are already merged
        thanks to Annotated reducers!
        """
        completed = state.get("completed_tasks", [])
        total_work_time = state.get("total_processing_time", 0.0)
        
        console.print(f"\n[bold magenta]>> AGGREGATION (All {len(completed)} tasks complete!)[/bold magenta]")
        console.print(f"[magenta]Total work time: {total_work_time:.2f}s[/magenta]")
        
        # Calculate additional metrics
        if completed:
            avg_time = sum(t["processing_time"] for t in completed) / len(completed)
            fastest = min(t["processing_time"] for t in completed)
            slowest = max(t["processing_time"] for t in completed)
            
            console.print(f"[magenta]Average: {avg_time:.2f}s, Range: {fastest:.1f}s - {slowest:.1f}s[/magenta]")
        
        return state
    
    async def _finalize(self, state: CompleteState) -> CompleteState:
        """Finalize and show summary."""
        total_elapsed = time.time() - state["session_start"]
        completed = state.get("completed_tasks", [])
        
        console.print(f"\n[bold cyan]>> Final Summary[/bold cyan]")
        console.print(f"[green]Tasks completed: {len(completed)}[/green]")
        console.print(f"[cyan]Wall clock time: {total_elapsed:.2f}s[/cyan]")
        console.print(f"[yellow]Critical sections: {self._critical_count}[/yellow]")
        
        # PROOF: Show actual max concurrent tasks reached
        console.print(f"\n[bold magenta]>> Concurrency Verification[/bold magenta]")
        console.print(f"[magenta]Max concurrent tasks reached: {self._max_concurrent_reached}[/magenta]")
        console.print(f"[dim](This proves max_concurrency config is working!)[/dim]")
        
        if completed:
            total_work = sum(t["processing_time"] for t in completed)
            speedup = total_work / total_elapsed if total_elapsed > 0 else 1
            console.print(f"\n[bold yellow]Speedup: {speedup:.2f}x[/bold yellow]")
        
        return state


# ==================== Main Demo ====================

async def run_complete_demo(num_tasks: int = 8, max_concurrent: int = 3):
    """Run demo with complete best practices."""
    workflow = CompleteParallelWorkflow()
    
    initial_state: CompleteState = {
        "task_ids": list(range(1, num_tasks + 1)),
    }
    
    # THE COMPLETE CONFIG:
    # 1. max_concurrency - LangGraph limits parallel tasks
    # 2. recursion_limit - Prevents infinite loops
    config = {
        "max_concurrency": max_concurrent,  # ← Built-in concurrency control!
        "recursion_limit": 100,
    }
    
    console.print(f"\n[bold]Running with max_concurrency={max_concurrent}[/bold]")
    console.print(f"[dim]Config: {config}[/dim]\n")
    
    final_state = await workflow.graph.ainvoke(initial_state, config=config)
    
    return final_state


async def demo_comparison():
    """Compare different concurrency levels."""
    console.print("""
[bold cyan]================================================================
  Complete Pattern: max_concurrency Comparison
================================================================[/bold cyan]
    """)
    
    for max_concurrent in [1, 2, 4]:
        console.print(f"\n[bold magenta]>>> max_concurrency={max_concurrent}[/bold magenta]")
        await run_complete_demo(num_tasks=8, max_concurrent=max_concurrent)
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    import sys
    
    console.print("""
[bold cyan]================================================================
  LangGraph Complete Parallel Pattern - BEST PRACTICES
  
  Uses:
  1. max_concurrency config (NO manual semaphore)
  2. Annotated reducers (auto state merge)
  3. defer=True (wait for all branches)
  4. Lock (critical sections only)
================================================================[/bold cyan]
    """)
    
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        asyncio.run(demo_comparison())
    else:
        num_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 8
        max_concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        asyncio.run(run_complete_demo(num_tasks, max_concurrent))
    
    console.print("\n[bold green]>> Demo complete![/bold green]")
    console.print("""
[bold yellow]KEY TAKEAWAYS:[/bold yellow]
1. Use config={{'max_concurrency': N}} - it's built into LangGraph!
2. Use Annotated for automatic result aggregation
3. Use defer=True on aggregation nodes to wait for all branches
4. Use Lock only for critical sections (like diff application)

[bold cyan]This is the COMPLETE pattern for Stomper![/bold cyan]
    """)

