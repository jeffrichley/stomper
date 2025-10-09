#!/usr/bin/env python
"""Demo: Visualize Stomper Workflow Graph

Shows the complete workflow graph in different formats:
- Mermaid syntax
- ASCII art
- PNG image

Run with: uv run python demo_workflow_visualization.py
"""

from pathlib import Path
from rich.console import Console
from stomper.workflow.orchestrator import StomperWorkflow

console = Console()


def demo_visualization():
    """Demo the workflow visualization."""
    console.print("\n[bold cyan]>> Stomper Workflow Visualization Demo[/bold cyan]\n")
    
    # Create workflow
    workflow = StomperWorkflow(
        project_root=Path("."),
        use_sandbox=True,
        run_tests=True,
        max_parallel_files=4,  # Show parallel-capable config
    )
    
    # 1. Mermaid syntax (for documentation)
    console.print("[bold yellow]1. Mermaid Syntax (for docs):[/bold yellow]")
    mermaid = workflow.visualize("mermaid")
    console.print("[dim]" + mermaid[:500] + "...[/dim]\n")
    
    # Save to file
    with open("workflow_diagram.mmd", "w") as f:
        f.write(mermaid)
    console.print("[green]Saved to: workflow_diagram.mmd[/green]\n")
    
    # 2. ASCII art (for terminal)
    console.print("[bold yellow]2. ASCII Art (for terminal):[/bold yellow]")
    try:
        ascii_graph = workflow.visualize("ascii")
        console.print(ascii_graph)
    except Exception as e:
        console.print(f"[dim]ASCII not available: {e}[/dim]\n")
    
    # 3. PNG image (for visualization)
    console.print("[bold yellow]3. PNG Image:[/bold yellow]")
    try:
        png_bytes = workflow.visualize("png")
        
        # Save to file
        with open("workflow_diagram.png", "wb") as f:
            f.write(png_bytes)
        
        console.print(f"[green]Saved PNG: workflow_diagram.png ({len(png_bytes)} bytes)[/green]")
        console.print("[dim]Open in image viewer to see the complete graph![/dim]\n")
        
    except Exception as e:
        console.print(f"[yellow]PNG generation requires mermaid.ink or pyppeteer[/yellow]")
        console.print(f"[dim]Error: {e}[/dim]\n")
    
    # Show graph structure
    console.print("\n[bold cyan]>> Graph Structure:[/bold cyan]")
    graph = workflow.graph.get_graph()
    
    console.print(f"[cyan]Total Nodes: {len(graph.nodes)}[/cyan]")
    
    # Show key workflow nodes (excluding start/end)
    workflow_nodes = [n for n in sorted(graph.nodes.keys()) if not n.startswith("__")]
    console.print(f"[cyan]Workflow Nodes ({len(workflow_nodes)}):[/cyan]")
    for node in workflow_nodes:
        console.print(f"  - {node}")
    
    console.print("\n[green]Visualization complete![/green]")
    console.print("\n[bold]Files created:[/bold]")
    console.print("  - workflow_diagram.mmd (Mermaid syntax)")
    console.print("  - workflow_diagram.png (if PNG generation succeeded)")
    console.print("\n[dim]Use these for documentation or debugging![/dim]\n")


if __name__ == "__main__":
    demo_visualization()

