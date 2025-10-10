"""Debug script to test parallel workflow with breakpoints.

Usage:
    1. Set breakpoints in this file or in orchestrator.py
    2. Run: uv run python debug_parallel_workflow.py
    3. Or use the "Debug Custom Script" configuration in VS Code
"""
import asyncio
from pathlib import Path

from stomper.ai.agent_manager import AgentManager
from stomper.ai.mapper import ErrorMapper
from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.sandbox_manager import SandboxManager
from stomper.quality.manager import QualityManager
from stomper.workflow.orchestrator import StomperWorkflow


async def main():
    """Run workflow with debugging."""
    project_root = Path("test_errors")  # Directory with test files

    # Configuration - MODIFY THESE FOR DIFFERENT TESTS
    config = {
        "project_root": project_root,
        "enabled_tools": ["ruff"],  # Try: ["ruff", "mypy"]
        "use_sandbox": True,  # Set to False for simpler debugging
        "run_tests": False,
        "max_parallel_files": 2,  # 1=sequential (easier), 2+=parallel
    }

    print("="*60)
    print("🐛 STOMPER DEBUG SESSION")
    print("="*60)
    print(f"Project root: {project_root.absolute()}")
    print(f"Tools: {config['enabled_tools']}")
    print(f"Use sandbox: {config['use_sandbox']}")
    print(f"Max parallel files: {config['max_parallel_files']}")
    print("="*60)
    print()

    # Initialize components
    quality_manager = QualityManager(project_root)
    agent_manager = AgentManager(project_root)
    prompt_generator = PromptGenerator()
    mapper = ErrorMapper()

    sandbox_manager = None
    if config["use_sandbox"]:
        sandbox_manager = SandboxManager(project_root)

    # Create workflow
    workflow = StomperWorkflow(
        project_root=project_root,
        quality_manager=quality_manager,
        agent_manager=agent_manager,
        prompt_generator=prompt_generator,
        mapper=mapper,
        sandbox_manager=sandbox_manager,
        run_tests_enabled=config["run_tests"],
        use_sandbox=config["use_sandbox"],
        max_parallel_files=config["max_parallel_files"],
    )

    # 🔴 SET BREAKPOINT HERE to step through workflow
    print("🚀 Starting workflow execution...")
    print("   (Set breakpoints in orchestrator.py to debug)")
    print()

    result = await workflow.run(config)

    # Print results
    print()
    print("="*60)
    print("✅ WORKFLOW COMPLETE")
    print("="*60)
    print(f"Successful fixes: {result.get('successful_fixes', [])}")
    print(f"Failed fixes: {result.get('failed_fixes', [])}")
    print(f"Total errors fixed: {result.get('total_errors_fixed', 0)}")
    print("="*60)

    # Print file status
    if result.get("files"):
        print()
        print("📊 FILE STATUS:")
        for file_state in result["files"]:
            status = "✅" if str(file_state.file_path) in result.get("successful_fixes", []) else "❌"
            print(f"  {status} {file_state.file_path}")
            print(f"     Fixed: {len(file_state.fixed_errors)} errors")
            print(f"     Remaining: {len(file_state.errors)} errors")
        print()


if __name__ == "__main__":
    # 💡 DEBUGGING TIPS:
    #
    # Key breakpoint locations in orchestrator.py:
    #
    # 1. Line ~668: _fan_out_files() - See Send() objects created
    # 2. Line ~297: _process_single_file_complete() - See each file start
    # 3. Line ~690: async with self._diff_application_lock - Critical section
    # 4. Line ~563: _aggregate_results() - See final merged results
    #
    # Try different configs:
    # - max_parallel_files=1 for sequential (easier to debug)
    # - max_parallel_files=2 to see parallelism
    # - use_sandbox=False for simpler execution

    asyncio.run(main())
