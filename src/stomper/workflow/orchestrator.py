"""LangGraph workflow orchestrator for Stomper."""

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import tempfile
from typing import Any

from git import Repo
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from stomper.ai.agent_manager import AgentManager
from stomper.ai.mapper import ErrorMapper
from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.sandbox_manager import SandboxManager
from stomper.quality.manager import QualityToolManager
from stomper.workflow.state import ErrorInfo, FileState, ProcessingStatus, StomperState

logger = logging.getLogger(__name__)


class StomperWorkflow:
    """LangGraph workflow orchestrator for Stomper."""

    def __init__(
        self,
        project_root: Path,
        use_sandbox: bool = True,
        run_tests: bool = True,
        max_parallel_files: int = 1,
    ):
        """Initialize workflow orchestrator.

        Args:
            project_root: Root directory of project
            use_sandbox: Whether to use git worktree sandbox
            run_tests: Whether to run tests after fixes
            max_parallel_files: Maximum files to process in parallel (1=sequential)
        """
        self.project_root = Path(project_root)
        self.use_sandbox = use_sandbox
        self.run_tests_enabled = run_tests
        self.max_parallel_files = max_parallel_files

        # Initialize components
        self.mapper = ErrorMapper(project_root=project_root)
        self.agent_manager = AgentManager(project_root=project_root, mapper=self.mapper)
        self.prompt_generator = PromptGenerator(
            project_root=project_root,
            mapper=self.mapper,
        )
        self.quality_manager = QualityToolManager()

        if use_sandbox:
            self.sandbox_manager = SandboxManager(project_root=project_root)
        else:
            self.sandbox_manager = None

        # Parallel safety lock for diff application
        self._diff_application_lock = asyncio.Lock()

        # Build graph
        self.graph = self._build_graph()

    def register_agent(self, name: str, agent: Any) -> None:
        """Register an AI agent.

        Args:
            name: Agent name
            agent: Agent instance
        """
        self.agent_manager.register_agent(name, agent)

    def visualize(self, output_format: str = "png") -> bytes | str:
        """Visualize the workflow graph.
        
        Args:
            output_format: Output format - "png", "mermaid", or "ascii"
            
        Returns:
            PNG bytes, Mermaid string, or ASCII string based on format
            
        Example:
            # Display in Jupyter
            from IPython.display import Image, display
            display(Image(workflow.visualize("png")))
            
            # Save to file
            with open("workflow.png", "wb") as f:
                f.write(workflow.visualize("png"))
            
            # Print Mermaid
            print(workflow.visualize("mermaid"))
        """
        graph_obj = self.graph.get_graph()
        
        if output_format == "png":
            return graph_obj.draw_mermaid_png()
        elif output_format == "mermaid":
            return graph_obj.draw_mermaid()
        elif output_format == "ascii":
            return graph_obj.draw_ascii()
        else:
            raise ValueError(f"Unknown format: {output_format}. Use 'png', 'mermaid', or 'ascii'")

    def _build_graph(self) -> Any:
        """Build LangGraph state machine with TRUE parallel processing using Send() API."""
        workflow = StateGraph(StomperState)

        # ==================== Add All Nodes ====================

        # Sequential initialization
        workflow.add_node("initialize", self._initialize_session)
        workflow.add_node("collect_errors", self._collect_all_errors)

        # Parallel per-file processing (using Send() API)
        # Each file gets processed in its own parallel branch
        workflow.add_node("process_single_file", self._process_single_file_complete)

        # Aggregation node with defer=True (waits for ALL parallel branches!)
        workflow.add_node("aggregate_results", self._aggregate_results, defer=True)
        
        # Final cleanup
        workflow.add_node("cleanup", self._cleanup_session)

        # ==================== Set Entry Point ====================

        workflow.set_entry_point("initialize")

        # ==================== Build Edge Structure ====================

        # Sequential initialization
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "collect_errors")

        # Fan-out to parallel processing using Send() API
        # LangGraph will process all files in parallel (up to max_concurrency limit)
        workflow.add_conditional_edges(
            "collect_errors",
            self._fan_out_files,
            # This returns either:
            # - List of Send() objects (one per file) for parallel processing
            # - "aggregate_results" if no files to process
        )

        # Each parallel file goes to aggregate after completing
        # aggregate_results has defer=True, so it waits for ALL files!
        workflow.add_edge("process_single_file", "aggregate_results")

        # After aggregation, cleanup
        workflow.add_edge("aggregate_results", "cleanup")
        workflow.add_edge("cleanup", END)

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
            "should_continue": True,
            "successful_fixes": [],
            "failed_fixes": [],
            "total_errors_fixed": 0,
            "status": ProcessingStatus.PENDING,
            # Attach components (not serialized)
            "agent_manager": self.agent_manager,
            "prompt_generator": self.prompt_generator,
            "mapper": self.mapper,
        }

        # Build runtime config with LangGraph's built-in concurrency control
        run_config = {
            "max_concurrency": self.max_parallel_files,  # LangGraph's built-in!
            "recursion_limit": 100,
        }

        logger.info("🚀 Starting Stomper workflow")
        logger.info(f"📊 Max parallel files: {self.max_parallel_files}")
        if self.max_parallel_files > 1:
            logger.info("⚡ Parallel processing enabled!")
        
        final_state = await self.graph.ainvoke(initial_state, config=run_config)
        logger.info(f"✅ Workflow complete: {final_state['status']}")

        return final_state

    # ==================== Node Implementations ====================

    async def _initialize_session(self, state: StomperState) -> StomperState:
        """Initialize the fixing session.

        Note: Worktree creation moved to per-file processing (_create_worktree node).
        """
        session_id = f"stomper-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        branch_name = f"stomper/auto-fixes-{session_id}"

        logger.info(f"📋 Initializing session: {session_id}")
        logger.info("ℹ️  Per-file worktree mode: Each file gets its own isolated environment")

        # NO worktree creation here! Created per-file in _create_worktree node
        state.update(
            {
                "session_id": session_id,
                "branch_name": branch_name,
                "sandbox_path": None,  # Will be created per file
                "current_worktree_id": None,
                "status": ProcessingStatus.IN_PROGRESS,
                "continue_on_error": state.get("continue_on_error", True),
                "test_validation": state.get("test_validation", "full"),
            }
        )

        return state

    async def _collect_all_errors(self, state: StomperState) -> StomperState:
        """Collect errors from all enabled quality tools.

        Note: ALWAYS runs in MAIN workspace (no worktree yet at this stage).
        """
        logger.info("🔍 Collecting errors from quality tools in MAIN workspace")

        # FORCE working_dir to be project_root (no sandbox at this stage)
        working_dir = state["project_root"]
        enabled_tools = state["enabled_tools"]

        files_with_errors: dict[Path, list[ErrorInfo]] = {}

        # Run all quality tools
        try:
            all_errors = self.quality_manager.run_tools(
                target_path=working_dir,
                project_root=working_dir,
                enabled_tools=enabled_tools,
                max_errors=state.get("max_errors_per_iteration", 100),
            )

            # Group by file
            for error in all_errors:
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
        except Exception as e:
            logger.warning(f"Failed to run quality tools: {e}")

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
        logger.info(f"Found {total_errors} errors in {len(file_states)} files")

        # If no files with errors, mark as completed and skip to cleanup
        if not file_states:
            state["status"] = ProcessingStatus.COMPLETED
            logger.info("✅ No errors found, skipping to cleanup")

        return state

    # ==================== Parallel File Processing (Send API) ====================

    async def _process_single_file_complete(self, state: dict) -> dict:
        """Process a single file completely (in parallel).
        
        This is the main parallel processing node - each file runs through this
        independently. LangGraph's max_concurrency limits how many run at once.
        
        Handles:
        - Worktree creation
        - Prompt generation with retry
        - AI agent fixing with retry
        - Verification
        - Testing
        - Diff extraction
        - LOCKED diff application to main
        - Commit in main
        - Worktree destruction
        
        Returns results for automatic aggregation via Annotated reducers.
        """
        if not state.get("current_file"):
            logger.warning("⚠️  No current_file in state")
            return {}
        
        current_file = state["current_file"]
        session_id = state["session_id"]
        working_dir = state["project_root"]
        
        logger.info(f"🚀 Processing {current_file.file_path} in parallel")
        
        worktree_path = None
        worktree_id = None
        
        try:
            # 1. Create worktree for THIS file
            if self.use_sandbox and self.sandbox_manager:
                file_stem = current_file.file_path.stem
                worktree_id = f"{session_id}_{file_stem}"
                
                logger.info(f"🏗️  Creating worktree for {current_file.file_path}")
                worktree_path = self.sandbox_manager.create_sandbox(
                    session_id=worktree_id,
                    base_branch="HEAD"
                )
                working_dir = worktree_path
                logger.info(f"✅ Worktree created: {worktree_path}")
            
            # 2. Process with retry logic
            max_attempts = current_file.max_attempts
            for attempt in range(max_attempts):
                current_file.attempts = attempt + 1
                
                try:
                    # 2a. Generate prompt
                    logger.info(f"📝 Generating prompt for {current_file.file_path} (attempt {attempt + 1})")
                    file_path = working_dir / current_file.file_path
                    code_context = file_path.read_text()
                    
                    from stomper.quality.base import QualityError
                    quality_errors = [
                        QualityError(
                            tool=err.tool,
                            file=err.file_path,
                            line=err.line_number,
                            column=err.column or 0,
                            code=err.code,
                            message=err.message,
                            severity=err.severity,
                            auto_fixable=err.auto_fixable,
                        )
                        for err in current_file.errors
                    ]
                    
                    prompt = state["prompt_generator"].generate_prompt(
                        errors=quality_errors,
                        code_context=code_context,
                        retry_count=attempt,
                    )
                    
                    # 2b. Call agent
                    logger.info(f"🤖 Calling agent for {current_file.file_path}")
                    error_context = {
                        "file_path": str(current_file.file_path),
                        "error_count": len(current_file.errors),
                    }
                    
                    fixed_code = state["agent_manager"].generate_fix_with_intelligent_fallback(
                        primary_agent_name="cursor-cli",
                        error=quality_errors[0] if quality_errors else None,
                        error_context=error_context,
                        code_context=code_context,
                        prompt=prompt,
                        max_retries=1,
                    )
                    
                    # Apply fix
                    file_path.write_text(fixed_code)
                    
                    # 2c. Verify fixes
                    logger.info(f"🔍 Verifying fixes for {current_file.file_path}")
                    new_errors = self.quality_manager.run_tools(
                        target_path=working_dir / current_file.file_path,
                        project_root=working_dir,
                        enabled_tools=state["enabled_tools"],
                        max_errors=100,
                    )
                    
                    # Compare errors
                    original_error_keys = {(e.tool, e.code, e.line_number) for e in current_file.errors}
                    new_error_keys = {(e.tool, e.code, e.line) for e in new_errors}
                    fixed_error_keys = original_error_keys - new_error_keys
                    
                    current_file.fixed_errors = [
                        e for e in current_file.errors 
                        if (e.tool, e.code, e.line_number) in fixed_error_keys
                    ]
                    current_file.errors = [
                        e for e in current_file.errors 
                        if (e.tool, e.code, e.line_number) in new_error_keys
                    ]
                    
                    logger.info(
                        f"Fixed {len(current_file.fixed_errors)} errors, "
                        f"{len(current_file.errors)} remaining"
                    )
                    
                    # If all fixed or max attempts, break retry loop
                    if not current_file.errors:
                        logger.info(f"✅ All errors fixed for {current_file.file_path}")
                        break
                    elif attempt + 1 >= max_attempts:
                        logger.warning(f"⚠️  Max attempts reached for {current_file.file_path}")
                        break
                    else:
                        logger.info(f"🔄 Retrying {current_file.file_path} (attempt {attempt + 2})")
                        continue
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {current_file.file_path}: {e}")
                    if attempt + 1 >= max_attempts:
                        raise
                    logger.info(f"🔄 Retrying after error (attempt {attempt + 2})")
                    continue
            
            # 3. Run tests (if enabled and errors were fixed)
            if self.run_tests_enabled and current_file.fixed_errors:
                logger.info(f"🧪 Running tests for {current_file.file_path}")
                try:
                    tool = self.quality_manager.tools.get("pytest")
                    if tool and tool.is_available():
                        test_errors = tool.run_tool(working_dir, working_dir)
                        if test_errors:
                            raise Exception(f"Tests failed: {len(test_errors)} failures")
                    logger.info("✅ Tests passed")
                except Exception as e:
                    logger.error(f"❌ Tests failed for {current_file.file_path}: {e}")
                    raise
            
            # 4. Extract diff (if using sandbox)
            diff_content = None
            if worktree_path:
                logger.info(f"📤 Extracting diff for {current_file.file_path}")
                worktree_repo = Repo(worktree_path)
                diff_content = worktree_repo.git.diff("HEAD")
                
                if diff_content:
                    logger.info(f"✅ Diff extracted ({len(diff_content)} bytes)")
                else:
                    logger.warning("⚠️  No changes detected")
            
            # 5. CRITICAL SECTION: Apply to main (MUST be serialized!)
            if diff_content:
                async with self._diff_application_lock:
                    logger.info(f"🔒 [LOCKED] Applying diff for {current_file.file_path}")
                    
                    try:
                        main_repo = Repo(self.project_root)
                    except Exception:
                        logger.warning("⚠️  Not a git repo - skipping diff application")
                    else:
                        # Write diff to temp file
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                            f.write(diff_content)
                            patch_file = f.name
                        
                        try:
                            # Apply patch
                            main_repo.git.apply(patch_file)
                            logger.info("✅ Patch applied to main workspace")
                            
                            # Commit in main
                            error_codes = [e.code for e in current_file.fixed_errors]
                            commit_msg = (
                                f"fix(quality): resolve {len(error_codes)} issues in {current_file.file_path.name}\n\n"
                                + "\n".join(f"- {code}" for code in error_codes)
                                + f"\n\nFixed by: stomper v{self._get_version()}"
                            )
                            
                            main_repo.index.add([str(current_file.file_path)])
                            main_repo.index.commit(commit_msg)
                            
                            logger.info(f"💾 Committed in main workspace")
                            
                        finally:
                            Path(patch_file).unlink(missing_ok=True)
                    
                    logger.info(f"🔓 [UNLOCKED] Diff applied for {current_file.file_path}")
            elif not self.use_sandbox:
                # Direct mode - file already modified, just record success
                logger.info("ℹ️  Direct mode - file modified in place")
            
            # 6. Cleanup worktree
            if worktree_path and self.sandbox_manager and worktree_id:
                logger.info(f"🗑️  Destroying worktree for {current_file.file_path}")
                try:
                    self.sandbox_manager.cleanup_sandbox(worktree_id)
                    logger.info(f"✅ Worktree destroyed")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to destroy worktree: {e}")
            
            # 7. Return results for aggregation
            logger.info(f"✅ Successfully processed {current_file.file_path}")
            
            return {
                "successful_fixes": [str(current_file.file_path)],
                "total_errors_fixed": len(current_file.fixed_errors),
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process {current_file.file_path}: {e}")
            
            # Cleanup worktree on error
            if worktree_path and self.sandbox_manager and worktree_id:
                try:
                    logger.info(f"🧹 Cleaning up worktree after error")
                    self.sandbox_manager.cleanup_sandbox(worktree_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup: {cleanup_error}")
            
            # Return failure for aggregation
            return {
                "failed_fixes": [str(current_file.file_path)],
            }

    # ==================== Helper Methods ====================
    
    def _get_version(self) -> str:
        """Get stomper version."""
        try:
            import stomper
            return stomper.__version__
        except Exception:
            return "unknown"
    
    # ==================== REMOVED: Legacy Sequential Nodes ====================
    # The following sequential nodes have been REMOVED in favor of true parallel processing.
    # All functionality is now consolidated in _process_single_file_complete.
    #
    # Removed methods:
    # - _create_worktree, _generate_prompt, _call_agent
    # - _verify_file_fixes, _run_test_suite, _extract_diff  
    # - _apply_to_main, _commit_in_main, _destroy_worktree
    # - _move_to_next_file, _check_more_files, _should_continue_after_error
    # - _handle_processing_error, _destroy_worktree_on_error
    # - _retry_current_file, _should_retry_fixes, _check_test_results
    # ============================================================================

    async def _aggregate_results(self, state: StomperState) -> StomperState:
        """Aggregate results from all file processing.
        
        Note: This node has defer=True, so it waits until ALL parallel
        branches complete before executing. Perfect for final metrics!
        
        By the time we reach here, Annotated reducers have already merged:
        - successful_fixes (concatenated from all files)
        - failed_fixes (concatenated from all files)
        - total_errors_fixed (summed from all files)
        """
        successful = state.get("successful_fixes", [])
        failed = state.get("failed_fixes", [])
        total_fixed = state.get("total_errors_fixed", 0)
        
        logger.info("📊 Aggregating results from all files")
        logger.info(f"  ✅ Successful: {len(successful)}")
        logger.info(f"  ❌ Failed: {len(failed)}")
        logger.info(f"  🔧 Total errors fixed: {total_fixed}")
        
        return state

    async def _cleanup_session(self, state: StomperState) -> StomperState:
        """Clean up session resources.

        Note: Per-file worktrees should already be destroyed by _destroy_worktree.
        This is just final sanity checks and summary.
        """
        logger.info("🧹 Final session cleanup")

        # Save mapper learning data
        if state.get("mapper"):
            try:
                state["mapper"].save()
                logger.info("✅ Saved learning data")
            except Exception as e:
                logger.warning(f"Failed to save mapper data: {e}")

        # Sanity check: Verify no worktrees left (shouldn't happen in per-file mode)
        if state.get("sandbox_path"):
            logger.warning("⚠️  Worktree still exists - this shouldn't happen in per-file mode!")
            # Try to clean it up anyway
            if self.sandbox_manager and state.get("current_worktree_id"):
                try:
                    self.sandbox_manager.cleanup_sandbox(state["current_worktree_id"])
                    logger.info("✅ Cleaned up orphaned worktree")
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned worktree: {e}")

        # Final status
        if state["status"] != ProcessingStatus.FAILED:
            state["status"] = ProcessingStatus.COMPLETED

        # Generate summary
        logger.info(
            f"🎉 Session complete:\n"
            f"  - Files fixed: {len(state['successful_fixes'])}\n"
            f"  - Files failed: {len(state['failed_fixes'])}\n"
            f"  - Total errors fixed: {state['total_errors_fixed']}"
        )

        return state

    # ==================== Helper Methods ====================

    def _get_diff_lock(self) -> asyncio.Lock:
        """Get lock for diff application (parallel safety).

        Returns:
            Asyncio lock for serializing diff application
        """
        return self._diff_application_lock

    def _fan_out_files(self, state: StomperState):
        """Fan out files to parallel processing using Send() API.
        
        Returns list of Send() objects (one per file) for parallel execution.
        LangGraph will process all Send() objects concurrently (up to max_concurrency).
        
        Args:
            state: Current workflow state
            
        Returns:
            List of Send() objects for parallel processing, or "aggregate_results" if no files
        """
        files = state.get("files", [])
        
        if not files:
            logger.info("✅ No files with errors to process")
            return "aggregate_results"  # Skip directly to aggregation
        
        logger.info(f"📋 Fanning out {len(files)} files to parallel processing")
        logger.info(f"⚡ Max concurrent: {self.max_parallel_files}")
        
        # Send each file to parallel processing
        # LangGraph will execute these concurrently (respecting max_concurrency)!
        return [
            Send("process_single_file", {
                **state,
                "current_file": file,  # Each parallel branch gets its file
            })
            for file in files
        ]

    def _should_continue_after_error(self, state: StomperState) -> str:
        """Decide whether to continue after error.

        Args:
            state: Current workflow state

        Returns:
            "continue" to process more files, "abort" to stop
        """
        continue_on_error = state.get("continue_on_error", True)
        has_more_files = state["current_file_index"] + 1 < len(state.get("files", []))

        if continue_on_error and has_more_files:
            logger.info("⏭️  Continuing with next file after error")
            return "continue"

        logger.info("🛑 Aborting workflow after error")
        return "abort"
