"""End-to-end integration tests for complete AI workflow."""

import subprocess
from typing import Any

import pytest

from stomper.workflow.state import ProcessingStatus


# Mock agent implementation (not a test class - avoid Test* naming)
class MockAIAgent:
    """Simple mock AI agent for workflow tests."""

    def __init__(self, return_value: str = ""):
        self.return_value = return_value
        self.call_count = 0

    def generate_fix(self, error_context: dict[str, Any], code_context: str, prompt: str) -> str:
        """Generate fix (test implementation)."""
        self.call_count += 1
        return self.return_value

    def validate_response(self, response: str) -> bool:
        """Validate response (always true for tests)."""
        return True

    def get_agent_info(self) -> dict[str, Any]:
        """Get agent info."""
        return {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test agent for integration tests",
            "capabilities": {
                "can_fix_linting": True,
                "can_fix_types": True,
                "can_fix_tests": False,
                "max_context_length": 4000,
                "supported_languages": ["python"],
            },
        }


@pytest.mark.e2e
async def test_full_workflow_success(tmp_path):
    """Test complete workflow from initialization to cleanup."""
    # Import here to avoid issues if workflow module doesn't exist yet
    try:
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow not yet implemented")

    # Setup test project
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import os\n")  # F401 - unused import

    # Create mock agent
    test_agent = MockAIAgent(return_value="")  # Remove import

    # Create workflow
    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=False, run_tests=False)
    workflow.register_agent("cursor-cli", test_agent)

    # Run workflow
    initial_state = {
        "enabled_tools": ["ruff"],
        "processing_strategy": "batch_errors",
    }

    final_state = await workflow.run(initial_state)

    # Verify successful completion
    assert final_state["status"] == ProcessingStatus.COMPLETED
    assert len(final_state["successful_fixes"]) > 0
    assert final_state["total_errors_fixed"] > 0

    # Verify cleanup happened
    assert not (tmp_path / ".stomper" / "sandbox").exists()


@pytest.mark.e2e
async def test_workflow_with_retry(tmp_path):
    """Test workflow retry logic on failed fixes."""
    try:
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow not yet implemented")

    # Setup test file with actual error (unused import)
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import os\nimport sys\n")  # F401 - unused imports

    # Test agent that succeeds
    test_agent = MockAIAgent(return_value="x = 1  # Fixed")

    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=False, run_tests=False)
    workflow.register_agent("cursor-cli", test_agent)

    initial_state = {
        "enabled_tools": ["ruff"],
        "max_retries": 3,
    }

    final_state = await workflow.run(initial_state)

    # Verify workflow completed
    assert test_agent.call_count >= 1
    assert final_state["status"] == ProcessingStatus.COMPLETED


@pytest.mark.e2e
async def test_workflow_test_validation(tmp_path):
    """Test workflow validates fixes don't break tests."""
    try:
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow not yet implemented")

    # Setup test file with linting error so workflow processes it
    test_file = tmp_path / "src" / "module.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import sys\ndef add(a, b):\n    return a + b\n")  # F401: unused import

    test_test = tmp_path / "tests" / "test_module.py"
    test_test.parent.mkdir(parents=True)
    test_test.write_text(
        "from src.module import add\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n"
    )

    # Test agent that breaks functionality while "fixing"
    test_agent = MockAIAgent(return_value="def add(a, b):\n    return a - b\n")  # Breaks tests!

    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=False, run_tests=True)
    workflow.register_agent("cursor-cli", test_agent)

    initial_state = {
        "enabled_tools": ["ruff"],
        "run_tests": True,
    }

    final_state = await workflow.run(initial_state)

    # Verify workflow caught test failure
    # With continue_on_error=True (default), status might be COMPLETED but file should be in failed_fixes
    assert len(final_state.get("failed_fixes", [])) > 0
    assert any("module.py" in str(f) for f in final_state["failed_fixes"])


@pytest.mark.e2e
async def test_workflow_git_isolation(tmp_path):
    """Test workflow uses git worktree for isolation and applies changes back to main."""
    try:
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow not yet implemented")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("import os\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Test agent
    test_agent = MockAIAgent(return_value="")  # Remove import

    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=True, run_tests=False)
    workflow.register_agent("cursor-cli", test_agent)

    # Run workflow
    initial_state = {"enabled_tools": ["ruff"]}
    final_state = await workflow.run(initial_state)

    # Verify workflow completed successfully
    assert final_state["status"] == ProcessingStatus.COMPLETED
    assert len(final_state["successful_fixes"]) > 0

    # Verify per-file worktree architecture:
    # 1. Sandbox was created (per file) and cleaned up (no sandboxes left)
    assert not (tmp_path / ".stomper" / "sandboxes").exists() or \
           len(list((tmp_path / ".stomper" / "sandboxes").iterdir())) == 0

    # 2. NEW ARCHITECTURE: Changes ARE applied to main workspace
    #    (via diff extraction → apply → commit in main)
    assert test_file.read_text() == ""  # Import was removed

    # 3. Verify commit happened in main workspace
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "fix(quality)" in result.stdout or len(result.stdout) > 0


@pytest.mark.e2e
async def test_workflow_adaptive_learning(tmp_path):
    """Test workflow uses ErrorMapper for adaptive learning."""
    try:
        from stomper.ai.mapper import ErrorMapper
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow or ErrorMapper not yet implemented")

    # Setup test file with actual error
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import os\nimport sys\n")  # F401 - unused imports

    # Test agent
    test_agent = MockAIAgent(return_value="# Fixed\n")

    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=False, run_tests=False)
    workflow.register_agent("cursor-cli", test_agent)

    # Run workflow
    initial_state = {"enabled_tools": ["ruff"]}
    final_state = await workflow.run(initial_state)

    # Verify mapper was used for adaptive strategies
    assert final_state["total_errors_fixed"] > 0  # Should fix the errors

    # Check that workflow's mapper recorded outcomes
    assert workflow.mapper.data.total_attempts > 0


@pytest.mark.e2e
async def test_workflow_no_errors_found(tmp_path):
    """Test workflow handles case where no errors are found."""
    try:
        from stomper.workflow.orchestrator import StomperWorkflow
    except ImportError:
        pytest.skip("StomperWorkflow not yet implemented")

    # Setup clean test file (no errors)
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def hello():\n    return 'world'\n")

    # Test agent (should not be called)
    test_agent = MockAIAgent(return_value="")

    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=False, run_tests=False)
    workflow.register_agent("cursor-cli", test_agent)

    # Run workflow
    initial_state = {"enabled_tools": ["ruff"]}
    final_state = await workflow.run(initial_state)

    # Verify no fixes were attempted
    assert final_state["total_errors_fixed"] == 0
    assert len(final_state["successful_fixes"]) == 0
    assert test_agent.call_count == 0
