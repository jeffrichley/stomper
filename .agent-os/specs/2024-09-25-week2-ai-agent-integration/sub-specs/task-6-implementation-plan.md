# Task 6 Implementation Plan: AI Agent Workflow Integration with LangGraph

> **Status:** Ready for Implementation  
> **Created:** 2025-10-08  
> **Parent Task:** Task 6 - AI Agent Workflow Integration  
> **Prerequisites:** ✅ Tasks 1-5 Complete (AIAgent, CursorClient, PromptGenerator, FixApplier, ErrorMapper)

---

## 📋 Overview

This plan integrates all AI agent components (Tasks 1-5) into a complete, end-to-end automated fixing workflow using **LangChain** and **LangGraph** for sophisticated state machine orchestration.

### What We're Building

A LangGraph-powered workflow that:
1. **Initializes** a fixing session with git worktree sandbox
2. **Collects errors** from quality tools
3. **Processes files** through AI agent with adaptive prompting
4. **Validates fixes** by re-running quality tools
5. **Runs tests** to ensure no regressions
6. **Commits changes** with conventional commit messages
7. **Handles errors** with intelligent retry and fallback
8. **Cleans up** sandbox and provides session results

---

## 🎯 Goals

1. **Orchestrate Complex Workflow** - Use LangGraph state machine for multi-step processing
2. **Integrate All Components** - Connect AIAgent, PromptGenerator, FixApplier, Validator, ErrorMapper
3. **Safe Isolated Execution** - Use git worktrees for sandbox isolation
4. **Intelligent Error Handling** - Retry logic with adaptive strategies
5. **Comprehensive Validation** - Verify fixes don't break tests
6. **Complete CLI Integration** - Wire workflow into `stomper fix` command

---

## 🏗️ Architecture

### LangGraph State Machine

```
┌─────────────┐
│ Initialize  │ Create session, git worktree, branch
└──────┬──────┘
       ↓
┌─────────────┐
│   Collect   │ Run quality tools, gather errors
│   Errors    │
└──────┬──────┘
       ↓
┌─────────────┐
│  Process    │ Generate prompt, call AI agent
│    File     │ Apply fixes with ErrorMapper
└──────┬──────┘
       ↓
┌─────────────┐      retry
│   Verify    │ ←────────┐
│    Fixes    │          │
└──────┬──────┘          │
       ↓                 │
  [Fixed?]               │
   ↙    ↘                │
 YES    NO──[Retry?]────┘
  ↓          ↓
  │        ABORT
  ↓
┌─────────────┐
│  Run Tests  │ Execute pytest, validate no breaks
└──────┬──────┘
       ↓
  [Passed?]
   ↙    ↘
 YES    NO
  ↓      ↓
  │   [Handle
  │    Error]
  ↓      ↓
┌─────────────┐
│   Commit    │ Create conventional commit
│  Changes    │
└──────┬──────┘
       ↓
  [More Files?]
   ↙    ↘
 YES    NO
  ↓      ↓
[Next]   │
  │      ↓
  └────→ Cleanup
```

### Component Integration

```
StomperWorkflow (LangGraph)
    ├── AgentManager (Task 1) - Agent selection & fallback
    ├── CursorClient (Task 2) - AI agent execution
    ├── PromptGenerator (Task 3) - Adaptive prompt creation
    ├── FixApplier (Task 4) - Apply & validate fixes
    ├── ErrorMapper (Task 5) - Learning & adaptation
    ├── SandboxManager (NEW) - Git worktree management
    └── QualityToolManager (Existing) - Run quality tools
```

---

## 📝 Implementation Tasks

### Task 6.1: Write Integration Tests for Complete Workflow ✅

**Estimated Time:** 3-4 hours

#### What to Test

1. **Full End-to-End Workflow**
   - Initialize → Collect → Process → Verify → Test → Commit → Cleanup
   - With mocked AI agent responses
   - Verify state transitions

2. **Error Handling Paths**
   - Retry logic works correctly
   - Max retries respected
   - Fallback strategies applied
   - Cleanup happens on failure

3. **Git Worktree Integration**
   - Sandbox created correctly
   - Changes isolated from main workspace
   - Cleanup removes sandbox

4. **Adaptive Learning**
   - ErrorMapper records outcomes
   - PromptGenerator uses adaptive strategies
   - Success rates improve over iterations

#### Test File Structure

Create `tests/e2e/test_workflow_integration.py`:

```python
"""End-to-end integration tests for complete AI workflow."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from stomper.workflow.orchestrator import StomperWorkflow
from stomper.workflow.state import StomperState, ProcessingStatus
from stomper.quality.base import QualityError


@pytest.mark.e2e
async def test_full_workflow_success(tmp_path):
    """Test complete workflow from initialization to cleanup."""
    # Setup test project
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import os\n")  # F401 - unused import
    
    # Mock AI agent
    mock_agent = Mock()
    mock_agent.generate_fix.return_value = ""  # Remove import
    
    # Create workflow
    workflow = StomperWorkflow(project_root=tmp_path)
    workflow.register_agent("cursor-cli", mock_agent)
    
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
    # Setup test file with difficult error
    test_file = tmp_path / "src" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("x = 1" + " " * 100)  # E501 - line too long
    
    # Mock AI agent that fails first, succeeds second
    mock_agent = Mock()
    mock_agent.generate_fix.side_effect = [
        Exception("First attempt failed"),  # Fail
        "x = 1  # Fixed"  # Success
    ]
    
    workflow = StomperWorkflow(project_root=tmp_path)
    workflow.register_agent("cursor-cli", mock_agent)
    
    initial_state = {
        "enabled_tools": ["ruff"],
        "max_retries": 3,
    }
    
    final_state = await workflow.run(initial_state)
    
    # Verify retry happened
    assert mock_agent.generate_fix.call_count == 2
    assert final_state["status"] == ProcessingStatus.COMPLETED


@pytest.mark.e2e
async def test_workflow_test_validation(tmp_path):
    """Test workflow validates fixes don't break tests."""
    # Setup test file and test
    test_file = tmp_path / "src" / "module.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def add(a, b):\n    return a + b\n")
    
    test_test = tmp_path / "tests" / "test_module.py"
    test_test.parent.mkdir(parents=True)
    test_test.write_text(
        "from src.module import add\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n"
    )
    
    # Mock AI agent that breaks functionality
    mock_agent = Mock()
    mock_agent.generate_fix.return_value = "def add(a, b):\n    return a - b\n"  # Wrong!
    
    workflow = StomperWorkflow(project_root=tmp_path)
    workflow.register_agent("cursor-cli", mock_agent)
    
    initial_state = {
        "enabled_tools": ["ruff"],
        "run_tests": True,
    }
    
    final_state = await workflow.run(initial_state)
    
    # Verify workflow caught test failure
    assert final_state["status"] == ProcessingStatus.FAILED
    assert "test" in final_state["error_message"].lower()


@pytest.mark.e2e  
async def test_workflow_git_isolation(tmp_path):
    """Test workflow uses git worktree for isolation."""
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path)
    
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("import os\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)
    
    # Mock AI agent
    mock_agent = Mock()
    mock_agent.generate_fix.return_value = ""  # Remove import
    
    workflow = StomperWorkflow(project_root=tmp_path, use_sandbox=True)
    workflow.register_agent("cursor-cli", mock_agent)
    
    # Capture sandbox path
    sandbox_path = None
    original_create = workflow._create_sandbox
    def capture_sandbox(session_id):
        nonlocal sandbox_path
        sandbox_path = original_create(session_id)
        return sandbox_path
    workflow._create_sandbox = capture_sandbox
    
    # Run workflow
    await workflow.run({"enabled_tools": ["ruff"]})
    
    # Verify sandbox was created and used
    assert sandbox_path is not None
    assert "stomper" in str(sandbox_path)
    
    # Verify main workspace unchanged during processing
    assert test_file.read_text() == "import os\n"
```

#### Acceptance Criteria for 6.1

- [ ] End-to-end workflow test passes
- [ ] Retry logic test passes
- [ ] Test validation test passes
- [ ] Git isolation test passes
- [ ] All tests use async/await correctly
- [ ] Mocking is comprehensive and realistic
- [ ] Tests run independently (no shared state)

---

### Task 6.2: Create LangGraph Workflow Orchestrator 🔧

**Estimated Time:** 4-5 hours

#### Create Workflow State Definition

**File:** `src/stomper/workflow/state.py`

```python
"""LangGraph state definitions for Stomper workflow."""

from enum import Enum
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel


class ProcessingStatus(str, Enum):
    """Status of file processing."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class ErrorInfo(BaseModel):
    """Information about a quality error."""
    
    tool: str
    code: str
    message: str
    file_path: Path
    line_number: int
    column: int | None = None
    severity: str = "error"
    auto_fixable: bool = False


class FileState(BaseModel):
    """State of a single file being processed."""
    
    file_path: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    errors: list[ErrorInfo] = []
    fixed_errors: list[ErrorInfo] = []
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    backup_path: Path | None = None


class StomperState(TypedDict, total=False):
    """Complete state for Stomper workflow."""
    
    # Session info
    session_id: str
    branch_name: str
    sandbox_path: Path | None
    project_root: Path
    
    # Configuration
    enabled_tools: list[str]
    processing_strategy: str
    max_errors_per_iteration: int
    run_tests: bool
    use_sandbox: bool
    
    # Current processing state
    files: list[FileState]
    current_file_index: int
    
    # Results
    successful_fixes: list[str]
    failed_fixes: list[str]
    total_errors_fixed: int
    
    # Control flow
    should_continue: bool
    status: ProcessingStatus
    error_message: str | None
    
    # Components (not serialized)
    agent_manager: object  # AgentManager instance
    prompt_generator: object  # PromptGenerator instance
    fix_applier: object  # FixApplier instance
    mapper: object  # ErrorMapper instance
```

#### Create LangGraph Workflow Orchestrator

**File:** `src/stomper/workflow/orchestrator.py`

```python
"""LangGraph workflow orchestrator for Stomper."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, END

from stomper.ai.agent_manager import AgentManager
from stomper.ai.cursor_client import CursorClient
from stomper.ai.fix_applier import FixApplier
from stomper.ai.mapper import ErrorMapper
from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.sandbox_manager import SandboxManager
from stomper.quality.manager import QualityToolManager
from stomper.workflow.state import (
    StomperState,
    FileState,
    ProcessingStatus,
    ErrorInfo,
)

logger = logging.getLogger(__name__)


class StomperWorkflow:
    """LangGraph workflow orchestrator for Stomper."""
    
    def __init__(
        self,
        project_root: Path,
        use_sandbox: bool = True,
        run_tests: bool = True,
    ):
        """Initialize workflow orchestrator.
        
        Args:
            project_root: Root directory of project
            use_sandbox: Whether to use git worktree sandbox
            run_tests: Whether to run tests after fixes
        """
        self.project_root = Path(project_root)
        self.use_sandbox = use_sandbox
        self.run_tests_enabled = run_tests
        
        # Initialize components
        self.mapper = ErrorMapper(project_root=project_root)
        self.agent_manager = AgentManager(project_root=project_root, mapper=self.mapper)
        self.prompt_generator = PromptGenerator(
            project_root=project_root,
            mapper=self.mapper,
        )
        self.fix_applier = FixApplier()
        self.quality_manager = QualityToolManager()
        
        if use_sandbox:
            self.sandbox_manager = SandboxManager(project_root=project_root)
        else:
            self.sandbox_manager = None
        
        # Build graph
        self.graph = self._build_graph()
    
    def register_agent(self, name: str, agent: Any) -> None:
        """Register an AI agent.
        
        Args:
            name: Agent name
            agent: Agent instance
        """
        self.agent_manager.register_agent(name, agent)
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph state machine."""
        workflow = StateGraph(StomperState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_session)
        workflow.add_node("collect_errors", self._collect_all_errors)
        workflow.add_node("process_file", self._process_current_file)
        workflow.add_node("verify_fixes", self._verify_file_fixes)
        workflow.add_node("run_tests", self._run_test_suite)
        workflow.add_node("commit_changes", self._commit_file_changes)
        workflow.add_node("next_file", self._move_to_next_file)
        workflow.add_node("cleanup", self._cleanup_session)
        workflow.add_node("handle_error", self._handle_processing_error)
        workflow.add_node("retry_file", self._retry_current_file)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges
        workflow.add_edge("initialize", "collect_errors")
        workflow.add_edge("collect_errors", "process_file")
        workflow.add_edge("process_file", "verify_fixes")
        
        # Conditional edges
        workflow.add_conditional_edges(
            "verify_fixes",
            self._should_retry_fixes,
            {
                "retry": "retry_file",
                "success": "run_tests" if self.run_tests_enabled else "commit_changes",
                "abort": "handle_error",
            }
        )
        
        workflow.add_edge("retry_file", "process_file")
        
        if self.run_tests_enabled:
            workflow.add_conditional_edges(
                "run_tests",
                self._check_test_results,
                {
                    "pass": "commit_changes",
                    "fail": "handle_error",
                }
            )
        
        workflow.add_conditional_edges(
            "commit_changes",
            self._check_more_files,
            {
                "next": "next_file",
                "done": "cleanup",
            }
        )
        
        workflow.add_edge("next_file", "process_file")
        workflow.add_edge("cleanup", END)
        workflow.add_edge("handle_error", "cleanup")
        
        return workflow.compile()
    
    async def run(self, config: dict[str, Any]) -> StomperState:
        """Run the complete workflow.
        
        Args:
            config: Initial configuration
        
        Returns:
            Final workflow state
        """
        initial_state: StomperState = {
            "project_root": self.project_root,
            "use_sandbox": self.use_sandbox,
            "run_tests": self.run_tests_enabled,
            "enabled_tools": config.get("enabled_tools", ["ruff"]),
            "processing_strategy": config.get("processing_strategy", "batch_errors"),
            "max_errors_per_iteration": config.get("max_errors_per_iteration", 5),
            "current_file_index": 0,
            "should_continue": True,
            "successful_fixes": [],
            "failed_fixes": [],
            "total_errors_fixed": 0,
            "status": ProcessingStatus.PENDING,
            # Attach components (not serialized)
            "agent_manager": self.agent_manager,
            "prompt_generator": self.prompt_generator,
            "fix_applier": self.fix_applier,
            "mapper": self.mapper,
        }
        
        logger.info("🚀 Starting Stomper workflow")
        final_state = await self.graph.ainvoke(initial_state)
        logger.info(f"✅ Workflow complete: {final_state['status']}")
        
        return final_state
    
    # ==================== Node Implementations ====================
    
    async def _initialize_session(self, state: StomperState) -> StomperState:
        """Initialize the fixing session."""
        session_id = f"stomper-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        branch_name = f"stomper/auto-fixes-{session_id}"
        
        logger.info(f"📋 Initializing session: {session_id}")
        
        # Create sandbox if enabled
        if self.use_sandbox and self.sandbox_manager:
            sandbox_path = self.sandbox_manager.create_sandbox(session_id)
            logger.info(f"🏗️  Created sandbox: {sandbox_path}")
        else:
            sandbox_path = None
            logger.info("⚠️  Running without sandbox (direct mode)")
        
        state.update({
            "session_id": session_id,
            "branch_name": branch_name,
            "sandbox_path": sandbox_path,
            "status": ProcessingStatus.IN_PROGRESS,
        })
        
        return state
    
    async def _collect_all_errors(self, state: StomperState) -> StomperState:
        """Collect errors from all enabled quality tools."""
        logger.info("🔍 Collecting errors from quality tools")
        
        working_dir = state.get("sandbox_path") or state["project_root"]
        enabled_tools = state["enabled_tools"]
        
        files_with_errors: dict[Path, list[ErrorInfo]] = {}
        
        # Run each quality tool
        for tool_name in enabled_tools:
            logger.debug(f"Running {tool_name}...")
            
            errors = self.quality_manager.run_tool(
                tool_name,
                working_dir=working_dir,
            )
            
            # Group by file
            for error in errors:
                file_path = Path(error.file)
                if file_path not in files_with_errors:
                    files_with_errors[file_path] = []
                
                files_with_errors[file_path].append(
                    ErrorInfo(
                        tool=error.tool,
                        code=error.code,
                        message=error.message,
                        file_path=file_path,
                        line_number=error.line,
                        column=error.column,
                        severity=error.severity,
                        auto_fixable=error.auto_fixable,
                    )
                )
        
        # Create FileState for each file with errors
        file_states = []
        for file_path, errors in files_with_errors.items():
            file_states.append(
                FileState(
                    file_path=file_path,
                    errors=errors,
                    max_attempts=state.get("max_retries", 3),
                )
            )
        
        state["files"] = file_states
        
        total_errors = sum(len(fs.errors) for fs in file_states)
        logger.info(
            f"Found {total_errors} errors in {len(file_states)} files"
        )
        
        return state
    
    async def _process_current_file(self, state: StomperState) -> StomperState:
        """Process the current file with AI agent."""
        current_file = state["files"][state["current_file_index"]]
        file_path = current_file.file_path
        
        logger.info(f"🤖 Processing {file_path} (attempt {current_file.attempts + 1})")
        
        current_file.status = ProcessingStatus.IN_PROGRESS
        current_file.attempts += 1
        
        try:
            # Read file content
            working_dir = state.get("sandbox_path") or state["project_root"]
            full_path = working_dir / file_path
            code_context = full_path.read_text()
            
            # Generate adaptive prompt
            prompt = state["prompt_generator"].generate_prompt(
                errors=current_file.errors,
                code_context=code_context,
                retry_count=current_file.attempts - 1,
            )
            
            # Call AI agent with intelligent fallback
            error_context = {
                "file_path": str(file_path),
                "error_count": len(current_file.errors),
            }
            
            fixed_code = state["agent_manager"].generate_fix_with_intelligent_fallback(
                primary_agent_name="cursor-cli",
                error=current_file.errors[0],  # Primary error
                error_context=error_context,
                code_context=code_context,
                prompt=prompt,
                max_retries=1,  # Single attempt per workflow retry
            )
            
            # Apply fix
            state["fix_applier"].apply_fix(
                file_path=full_path,
                fixed_content=fixed_code,
            )
            
            current_file.status = ProcessingStatus.COMPLETED
            logger.info(f"✅ Applied fix to {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process {file_path}: {e}")
            current_file.status = ProcessingStatus.FAILED
            current_file.last_error = str(e)
        
        return state
    
    async def _verify_file_fixes(self, state: StomperState) -> StomperState:
        """Verify fixes by re-running quality tools."""
        current_file = state["files"][state["current_file_index"]]
        file_path = current_file.file_path
        
        logger.info(f"🔍 Verifying fixes for {file_path}")
        
        # Re-run quality tools on this file
        working_dir = state.get("sandbox_path") or state["project_root"]
        
        new_errors = []
        for tool_name in state["enabled_tools"]:
            errors = self.quality_manager.run_tool(
                tool_name,
                working_dir=working_dir,
                files=[file_path],
            )
            new_errors.extend(errors)
        
        # Compare with original errors
        original_error_keys = {
            (e.tool, e.code, e.line_number) for e in current_file.errors
        }
        new_error_keys = {
            (e.tool, e.code, e.line) for e in new_errors
        }
        
        fixed_error_keys = original_error_keys - new_error_keys
        
        # Update file state
        current_file.fixed_errors = [
            e for e in current_file.errors
            if (e.tool, e.code, e.line_number) in fixed_error_keys
        ]
        current_file.errors = [
            e for e in current_file.errors
            if (e.tool, e.code, e.line_number) in new_error_keys
        ]
        
        state["total_errors_fixed"] += len(current_file.fixed_errors)
        
        logger.info(
            f"Fixed {len(current_file.fixed_errors)} errors, "
            f"{len(current_file.errors)} remaining"
        )
        
        return state
    
    def _should_retry_fixes(self, state: StomperState) -> str:
        """Decide whether to retry fixes."""
        current_file = state["files"][state["current_file_index"]]
        
        if not current_file.errors:
            return "success"
        elif current_file.attempts < current_file.max_attempts:
            return "retry"
        else:
            return "abort"
    
    async def _retry_current_file(self, state: StomperState) -> StomperState:
        """Prepare for retry with updated strategy."""
        current_file = state["files"][state["current_file_index"]]
        
        logger.info(f"🔄 Retrying {current_file.file_path}")
        current_file.status = ProcessingStatus.RETRYING
        
        return state
    
    async def _run_test_suite(self, state: StomperState) -> StomperState:
        """Run test suite to validate fixes."""
        logger.info("🧪 Running test suite")
        
        working_dir = state.get("sandbox_path") or state["project_root"]
        
        try:
            result = self.quality_manager.run_tool(
                "pytest",
                working_dir=working_dir,
            )
            
            if result.returncode == 0:
                logger.info("✅ All tests passed")
            else:
                state["error_message"] = f"Tests failed: {result.stderr}"
                logger.error(f"❌ Tests failed: {result.stderr}")
        
        except Exception as e:
            state["error_message"] = f"Test execution error: {str(e)}"
            logger.error(f"❌ Test execution error: {e}")
        
        return state
    
    def _check_test_results(self, state: StomperState) -> str:
        """Check if tests passed."""
        return "pass" if not state.get("error_message") else "fail"
    
    async def _commit_file_changes(self, state: StomperState) -> StomperState:
        """Commit changes for current file."""
        current_file = state["files"][state["current_file_index"]]
        file_path = current_file.file_path
        
        logger.info(f"💾 Committing changes for {file_path}")
        
        # Generate conventional commit message
        error_codes = [e.code for e in current_file.fixed_errors]
        commit_msg = f"fix(quality): resolve {len(error_codes)} issues in {file_path.name}\n\n"
        commit_msg += "\n".join(f"- {code}" for code in error_codes)
        commit_msg += f"\n\nFixed by: stomper v{self._get_version()}"
        
        # Commit in sandbox or main workspace
        working_dir = state.get("sandbox_path") or state["project_root"]
        
        # (Git commit implementation here)
        
        state["successful_fixes"].append(str(file_path))
        logger.info(f"✅ Committed {file_path}")
        
        return state
    
    def _check_more_files(self, state: StomperState) -> str:
        """Check if there are more files to process."""
        if state["current_file_index"] + 1 < len(state["files"]):
            return "next"
        else:
            return "done"
    
    async def _move_to_next_file(self, state: StomperState) -> StomperState:
        """Move to next file in processing queue."""
        state["current_file_index"] += 1
        logger.info(
            f"⏭️  Moving to file {state['current_file_index'] + 1} "
            f"of {len(state['files'])}"
        )
        return state
    
    async def _handle_processing_error(self, state: StomperState) -> StomperState:
        """Handle processing errors."""
        current_file = state["files"][state["current_file_index"]]
        
        logger.error(f"❌ Failed to fix {current_file.file_path}")
        state["failed_fixes"].append(str(current_file.file_path))
        state["status"] = ProcessingStatus.FAILED
        
        return state
    
    async def _cleanup_session(self, state: StomperState) -> StomperState:
        """Clean up session resources."""
        logger.info("🧹 Cleaning up session")
        
        # Save mapper learning data
        if state.get("mapper"):
            state["mapper"].save()
        
        # Remove sandbox if used
        if self.use_sandbox and self.sandbox_manager and state.get("sandbox_path"):
            self.sandbox_manager.cleanup_sandbox(state["session_id"])
            logger.info("✅ Sandbox cleaned up")
        
        # Final status
        if state["status"] != ProcessingStatus.FAILED:
            state["status"] = ProcessingStatus.COMPLETED
        
        logger.info(
            f"🎉 Session complete: "
            f"{len(state['successful_fixes'])} fixed, "
            f"{len(state['failed_fixes'])} failed, "
            f"{state['total_errors_fixed']} total errors fixed"
        )
        
        return state
    
    def _get_version(self) -> str:
        """Get stomper version."""
        from stomper import __version__
        return __version__
```

#### Acceptance Criteria for 6.2

- [ ] `workflow/state.py` defines complete state types
- [ ] `workflow/orchestrator.py` implements LangGraph workflow
- [ ] All state transitions work correctly
- [ ] Nodes are async and properly typed
- [ ] Components are properly integrated
- [ ] Logging is comprehensive
- [ ] Error handling is robust

---

### Task 6.3: Add AI Agent Options to CLI Configuration 🎛️

**Estimated Time:** 2-3 hours

#### Update CLI with Workflow Options

**File:** `src/stomper/cli.py` (modify existing `fix` command)

```python
@app.command()
def fix(
    # Existing parameters...
    
    # NEW: Workflow options
    use_sandbox: bool = typer.Option(
        True,
        "--sandbox/--no-sandbox",
        help="Use git worktree sandbox for isolated execution",
    ),
    run_tests: bool = typer.Option(
        True,
        "--test/--no-test",
        help="Run tests after fixes to validate no regressions",
    ),
    max_retries: int = typer.Option(
        3,
        "--max-retries",
        help="Maximum retry attempts per file",
    ),
    processing_strategy: str = typer.Option(
        "batch_errors",
        "--strategy",
        help="Processing strategy: batch_errors, one_error_type, all_errors",
    ),
    agent_name: str = typer.Option(
        "cursor-cli",
        "--agent",
        help="AI agent to use",
    ),
):
    """Fix code quality issues using AI agents."""
    from stomper.workflow.orchestrator import StomperWorkflow
    
    console.print("\n[bold blue]🚀 Stomper AI Workflow[/bold blue]\n")
    
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load(config_file)
    
    # Create workflow
    workflow = StomperWorkflow(
        project_root=Path.cwd(),
        use_sandbox=use_sandbox,
        run_tests=run_tests,
    )
    
    # Register AI agent
    if agent_name == "cursor-cli":
        from stomper.ai.cursor_client import CursorClient
        agent = CursorClient()
        workflow.register_agent("cursor-cli", agent)
    else:
        console.print(f"[red]Unknown agent: {agent_name}[/red]")
        raise typer.Exit(1)
    
    # Build workflow config
    workflow_config = {
        "enabled_tools": determine_enabled_tools(...),
        "processing_strategy": processing_strategy,
        "max_errors_per_iteration": max_errors,
        "max_retries": max_retries,
    }
    
    # Run workflow
    import asyncio
    final_state = asyncio.run(workflow.run(workflow_config))
    
    # Display results
    display_workflow_results(final_state)
    
    if final_state["status"] == ProcessingStatus.FAILED:
        raise typer.Exit(1)


def display_workflow_results(state: dict) -> None:
    """Display workflow results in rich format."""
    from rich.panel import Panel
    from rich.table import Table
    
    # Results table
    results_table = Table(title="🎯 Fix Results")
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Value", style="white")
    
    results_table.add_row("Status", f"[green]{state['status']}[/green]")
    results_table.add_row("Files Fixed", str(len(state['successful_fixes'])))
    results_table.add_row("Files Failed", str(len(state['failed_fixes'])))
    results_table.add_row("Total Errors Fixed", str(state['total_errors_fixed']))
    
    console.print(results_table)
    
    # Show failed files if any
    if state['failed_fixes']:
        console.print("\n[bold red]⚠️  Failed Files:[/bold red]")
        for file_path in state['failed_fixes']:
            console.print(f"  - {file_path}")
```

#### Update Configuration Models

**File:** `src/stomper/config/models.py` (add workflow config)

```python
class WorkflowConfig(BaseModel):
    """Workflow execution configuration."""
    
    use_sandbox: bool = True
    run_tests: bool = True
    max_retries: int = 3
    processing_strategy: str = "batch_errors"
    agent_name: str = "cursor-cli"


class StomperConfig(BaseModel):
    """Complete Stomper configuration."""
    
    # Existing fields...
    
    workflow: WorkflowConfig = WorkflowConfig()
```

#### Acceptance Criteria for 6.3

- [ ] CLI `fix` command supports workflow options
- [ ] `--sandbox/--no-sandbox` flag works
- [ ] `--test/--no-test` flag works
- [ ] `--max-retries` flag works
- [ ] `--strategy` flag works
- [ ] `--agent` flag works
- [ ] Configuration models updated
- [ ] Results displayed beautifully with rich

---

### Task 6.4: Implement End-to-End Error Fixing Workflow 🔄

**Estimated Time:** 3-4 hours

This is mostly done in Task 6.2 (orchestrator), but we need to ensure:

#### Create SandboxManager Integration

**File:** `src/stomper/ai/sandbox_manager.py` (update with worktree support)

```python
"""Git worktree sandbox manager."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manager for git worktree sandboxes."""
    
    def __init__(self, project_root: Path):
        """Initialize sandbox manager.
        
        Args:
            project_root: Root directory of project
        """
        self.project_root = Path(project_root)
        self.sandbox_dir = self.project_root / ".stomper" / "sandboxes"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
    
    def create_sandbox(self, session_id: str) -> Path:
        """Create git worktree sandbox.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Path to sandbox directory
        """
        # Create sandbox path
        sandbox_path = self.sandbox_dir / session_id
        
        # Create new branch in worktree
        branch_name = f"sbx/{session_id}"
        
        try:
            # Create worktree from HEAD
            subprocess.run(
                ["git", "worktree", "add", str(sandbox_path), "-b", branch_name, "HEAD"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
            
            logger.info(f"Created sandbox: {sandbox_path} (branch: {branch_name})")
            return sandbox_path
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create sandbox: {e.stderr}")
            raise RuntimeError(f"Failed to create git worktree: {e.stderr}")
    
    def cleanup_sandbox(self, session_id: str) -> None:
        """Clean up sandbox worktree.
        
        Args:
            session_id: Session identifier
        """
        sandbox_path = self.sandbox_dir / session_id
        branch_name = f"sbx/{session_id}"
        
        try:
            # Remove worktree
            subprocess.run(
                ["git", "worktree", "remove", str(sandbox_path), "--force"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
            
            # Delete branch
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
            
            logger.info(f"Cleaned up sandbox: {sandbox_path}")
        
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to cleanup sandbox: {e.stderr}")
    
    def get_sandbox_diff(self, session_id: str) -> str:
        """Get diff of changes in sandbox.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Git diff output
        """
        sandbox_path = self.sandbox_dir / session_id
        
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        return result.stdout
```

#### Acceptance Criteria for 6.4

- [ ] SandboxManager creates git worktrees correctly
- [ ] SandboxManager cleans up worktrees and branches
- [ ] Workflow runs in sandbox when enabled
- [ ] Workflow runs in main workspace when sandbox disabled
- [ ] Diffs can be extracted from sandbox
- [ ] All git operations are safe and isolated

---

### Task 6.5: Add Comprehensive Error Handling and Logging 📝

**Estimated Time:** 2-3 hours

#### Create Logging Configuration

**File:** `src/stomper/workflow/logging.py`

```python
"""Logging configuration for workflow."""

import logging
from pathlib import Path
from rich.logging import RichHandler


def setup_workflow_logging(
    level: str = "INFO",
    log_file: Path | None = None,
) -> None:
    """Setup logging for workflow.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
    """
    handlers = [
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False,
        )
    ]
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
    )
```

#### Add Error Recovery

Update orchestrator nodes with try/except and proper error handling:

```python
async def _process_current_file(self, state: StomperState) -> StomperState:
    """Process current file with comprehensive error handling."""
    current_file = state["files"][state["current_file_index"]]
    
    try:
        # Processing logic...
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        current_file.status = ProcessingStatus.FAILED
        current_file.last_error = f"File not found: {e}"
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess error: {e}")
        current_file.status = ProcessingStatus.FAILED
        current_file.last_error = f"Tool execution failed: {e.stderr}"
    
    except Exception as e:
        logger.exception(f"Unexpected error processing {current_file.file_path}")
        current_file.status = ProcessingStatus.FAILED
        current_file.last_error = f"Unexpected error: {str(e)}"
    
    return state
```

#### Acceptance Criteria for 6.5

- [ ] Rich logging configured with colors and formatting
- [ ] All workflow nodes have comprehensive error handling
- [ ] Errors are logged with appropriate levels
- [ ] Workflow can recover from errors gracefully
- [ ] Optional log file output supported

---

### Task 6.6: Verify All Tests Pass and Workflow Works End-to-End ✅

**Estimated Time:** 2-3 hours

#### Manual Testing Checklist

- [ ] Run `stomper fix` on a real project
- [ ] Verify sandbox is created correctly
- [ ] Verify errors are collected
- [ ] Verify AI agent generates fixes
- [ ] Verify fixes are applied
- [ ] Verify tests run
- [ ] Verify commits are created
- [ ] Verify sandbox cleanup happens
- [ ] Verify `stomper stats` shows learning data
- [ ] Run with `--verbose` and check logging
- [ ] Run with `--no-sandbox` and verify direct mode
- [ ] Run with `--no-test` and verify tests skipped

#### Automated Test Run

```bash
# Run all tests
just test

# Run only workflow integration tests
pytest tests/e2e/test_workflow_integration.py -v

# Run with coverage
pytest --cov=src/stomper/workflow tests/e2e/test_workflow_integration.py
```

#### Integration Verification

Create `tests/e2e/test_real_workflow.py` for manual/CI testing:

```python
"""Real-world workflow integration test (requires cursor-cli)."""

import pytest
from pathlib import Path

# Mark as integration test (requires real tools)
pytestmark = pytest.mark.integration


def test_real_workflow_with_sample_project(tmp_path):
    """Test workflow on a real sample project."""
    # Setup sample project with known issues
    sample_file = tmp_path / "sample.py"
    sample_file.write_text(
        "import os  # F401 - unused\n"
        "x = 1" + " " * 100 + "  # E501 - too long\n"
    )
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)
    
    # Run stomper fix
    from stomper.cli import app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fix", "--project-root", str(tmp_path)],
    )
    
    assert result.exit_code == 0
    assert "Fixed" in result.stdout
```

---

## ✅ Overall Acceptance Criteria

### Functional Requirements

- [ ] Complete workflow runs from initialization to cleanup
- [ ] All Tasks 1-5 components integrated correctly
- [ ] Git worktree sandbox isolation works
- [ ] Adaptive learning with ErrorMapper functional
- [ ] Test validation prevents broken fixes
- [ ] Conventional commits generated
- [ ] CLI commands work end-to-end

### Testing Requirements

- [ ] All unit tests pass (Tasks 1-5)
- [ ] All integration tests pass (Task 6.1)
- [ ] E2E workflow test passes
- [ ] Test coverage ≥80% for workflow code
- [ ] No linting errors (`ruff check`)
- [ ] No type errors (`mypy`)

### Documentation Requirements

- [ ] Workflow documentation updated
- [ ] CLI help text accurate
- [ ] Configuration examples provided
- [ ] Architecture diagram updated

---

## 🚀 Implementation Order

1. **Task 6.1** - Write integration tests (TDD approach)
2. **Task 6.2** - Create LangGraph workflow orchestrator
3. **Task 6.4** - Implement SandboxManager with worktrees
4. **Task 6.5** - Add error handling and logging
5. **Task 6.3** - Wire into CLI
6. **Task 6.6** - Verify and validate

**Total Estimated Time:** 16-22 hours (2-3 days)

---

## 📊 Success Metrics

After Task 6 completion, Stomper will:

- ✅ **Automatically fix code quality issues** end-to-end
- ✅ **Learn and adapt** through ErrorMapper
- ✅ **Safely isolate changes** via git worktrees
- ✅ **Validate fixes** through test execution
- ✅ **Provide rich feedback** via CLI
- ✅ **Be production-ready** for real-world use

---

## 🎉 Deliverable

A **fully functional AI-powered code quality fixing tool** that:
- Integrates all Week 2 components seamlessly
- Uses LangGraph for sophisticated workflow orchestration
- Maintains code safety through sandbox isolation
- Learns and improves over time
- Provides exceptional developer experience

**This completes Week 2 - AI Agent Integration! 🎊**

