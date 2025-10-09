#!/usr/bin/env python
"""Demo: LangGraph's BUILT-IN max_concurrency vs Manual Semaphore

This demonstrates:
1. LangGraph's built-in max_concurrency config parameter
2. Comparison with manual semaphore approach
3. When to use each approach

Run with: uv run python demo_langgraph_builtin_concurrency.py
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

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])
logger = logging.getLogger(__name__)
console = Console()


class TaskState(TypedDict, total=False):
    """State with result aggregation."""
    task_ids: list[int]
    max_concurrent: int
    current_task_id: int | None
    completed_tasks: Annotated[list[dict[str, Any]], add]
    total_time: float


class BuiltinConcurrencyDemo:
    """Demo using LangGraph's BUILT-IN max_concurrency."""
    
    def __init__(self):
        """Initialize demo - NO manual semaphore needed!"""
        self._lock = asyncio.Lock()  # Still need lock for critical sections
        self._critical_section_count = 0
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(TaskState)
        
        workflow.add_node("initialize", self._initialize)
        workflow.add_node("process_task", self._process_single_task)
        workflow.add_node("finalize", self._finalize)
        
        workflow.set_entry_point("initialize")
        workflow.add_conditional_edges("initialize", self._fan_out)
        workflow.add_edge("process_task", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _initialize(self, state: TaskState) -> TaskState:
        console.print("\n[bold cyan]>> Using LangGraph's Built-in Concurrency[/bold cyan]")
        return {
            **state,
            "completed_tasks": [],
            "total_time": time.time(),
        }
    
    def _fan_out(self, state: TaskState):
        if not state.get("task_ids"):
            return "finalize"
        return [
            Send("process_task", {**state, "current_task_id": task_id})
            for task_id in state["task_ids"]
        ]
    
    async def _process_single_task(self, state: dict) -> dict:
        """Process task - LangGraph handles concurrency limit!"""
        task_id = state["current_task_id"]
        
        # NO SEMAPHORE NEEDED! LangGraph limits concurrency for us
        logger.info(f"Started Task {task_id}")
        
        start = time.time()
        await asyncio.sleep(1 + (task_id % 3))  # Simulate work
        
        # Critical section still needs a lock
        async with self._lock:
            self._critical_section_count += 1
            logger.info(f"LOCK: Task {task_id} in critical section (#{self._critical_section_count})")
            await asyncio.sleep(0.3)
        
        elapsed = time.time() - start
        logger.info(f"DONE: Task {task_id} ({elapsed:.1f}s)")
        
        return {
            "completed_tasks": [{
                "task_id": task_id,
                "time": elapsed,
            }]
        }
    
    async def _finalize(self, state: TaskState) -> TaskState:
        total = time.time() - state["total_time"]
        console.print(f"\n[green]Completed: {len(state.get('completed_tasks', []))}[/green]")
        console.print(f"[cyan]Total time: {total:.2f}s[/cyan]")
        console.print(f"[yellow]Critical sections: {self._critical_section_count}[/yellow]")
        return state


async def demo_builtin_concurrency(num_tasks: int = 8, max_concurrent: int = 3):
    """Demo using LangGraph's built-in max_concurrency."""
    workflow = BuiltinConcurrencyDemo()
    
    initial_state: TaskState = {
        "task_ids": list(range(1, num_tasks + 1)),
        "max_concurrent": max_concurrent,
    }
    
    # THE MAGIC: Set max_concurrency in config!
    # LangGraph will automatically limit parallel execution
    config = {
        "max_concurrency": max_concurrent,  # ← LangGraph handles this!
    }
    
    console.print(f"\n[bold]Demo: {num_tasks} tasks, max_concurrent={max_concurrent}[/bold]")
    console.print(f"[dim]Using: config={{'max_concurrency': {max_concurrent}}}[/dim]\n")
    
    final_state = await workflow.graph.ainvoke(initial_state, config=config)
    return final_state


async def demo_comparison():
    """Compare different concurrency levels using built-in support."""
    console.print("""
[bold cyan]================================================================
  LangGraph Built-in max_concurrency Demo
================================================================[/bold cyan]
    """)
    
    for max_concurrent in [1, 2, 4]:
        await demo_builtin_concurrency(num_tasks=8, max_concurrent=max_concurrent)
        await asyncio.sleep(0.5)


async def demo_vs_manual():
    """Compare built-in vs manual semaphore."""
    console.print("""
[bold magenta]================================================================
  Built-in max_concurrency vs Manual Semaphore
================================================================[/bold magenta]
    """)
    
    # Built-in approach
    console.print("\n[bold cyan]1. Using LangGraph's max_concurrency (RECOMMENDED)[/bold cyan]")
    await demo_builtin_concurrency(num_tasks=6, max_concurrent=2)
    
    # Manual approach (from our other demo)
    console.print("\n[bold yellow]2. Using Manual Semaphore (MORE CONTROL)[/bold yellow]")
    console.print("[dim]See demo_langgraph_parallel.py for manual approach[/dim]")


if __name__ == "__main__":
    import sys
    
    console.print("""
[bold cyan]================================================================
  LangGraph Built-in Concurrency Control Demo
  
  KEY FINDING: LangGraph HAS built-in max_concurrency!
  Usage: config={'max_concurrency': N}
================================================================[/bold cyan]
    """)
    
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        asyncio.run(demo_comparison())
    elif len(sys.argv) > 1 and sys.argv[1] == "vs":
        asyncio.run(demo_vs_manual())
    else:
        num_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 8
        max_concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        asyncio.run(demo_builtin_concurrency(num_tasks, max_concurrent))
    
    console.print("\n[bold green]>> Demo complete![/bold green]")
    console.print("\n[bold yellow]TAKEAWAY: Use config={'max_concurrency': N} - it's built in![/bold yellow]\n")

