# Task 6 Documentation Summary: Key Requirements from Product Documentation

> **Purpose:** Comprehensive summary of all requirements and design decisions found in project documentation for Task 6 implementation  
> **Created:** 2025-10-08  
> **Sources:** All `.agent-os/product/` and `ideas/` documentation

---

## 📚 Documentation Sources Reviewed

1. ✅ `.agent-os/product/langgraph-workflow.md` - **PRIMARY SOURCE** for LangGraph design
2. ✅ `.agent-os/product/tech-stack.md` - Technology choices
3. ✅ `.agent-os/product/architecture.md` - Overall architecture
4. ✅ `.agent-os/product/cli-design.md` - CLI interface requirements
5. ✅ `.agent-os/product/decisions.md` - Product decisions log
6. ✅ `.agent-os/product/mission.md` - Mission and vision
7. ✅ `.agent-os/product/roadmap.md` - Development roadmap
8. ✅ `ideas/git_flow.md` - Git worktree strategy
9. ✅ `.agent-os/specs/.../technical-spec.md` - Technical requirements

---

## 🎯 Core Requirements from Documentation

### 1. LangGraph State Machine (Primary Requirement)

**Source:** `.agent-os/product/langgraph-workflow.md`

#### State Definition

The workflow **MUST** use this exact state structure:

```python
class StomperState(TypedDict):
    # Session info
    session_id: str
    branch_name: str
    
    # Processing config
    enabled_tools: List[str]
    processing_strategy: str
    max_errors_per_iteration: int
    
    # Current state
    files: List[FileState]
    current_file_index: int
    
    # Results
    successful_fixes: List[str]
    failed_fixes: List[str]
    total_errors_fixed: int
    
    # Control flow
    should_continue: bool
    error_message: Optional[str]
```

#### Workflow Graph Structure

The workflow **MUST** include these nodes:

1. `initialize` - Create session, git branch
2. `collect_errors` - Run quality tools
3. `process_file` - AI agent fixes
4. `verify_fixes` - Re-run quality tools
5. `run_tests` - Execute pytest
6. `commit_changes` - Create git commit
7. `next_file` - Move to next file
8. `cleanup` - Session cleanup
9. `handle_error` - Error recovery
10. `retry_file` - Retry with updated strategy

#### Conditional Edges

```python
workflow.add_conditional_edges(
    "verify_fixes",
    should_retry_fixes,
    {
        "retry": "retry_file",
        "success": "run_tests",
        "abort": "handle_error"
    }
)

workflow.add_conditional_edges(
    "run_tests",
    check_test_results,
    {
        "pass": "commit_changes",
        "fail": "handle_error"
    }
)

workflow.add_conditional_edges(
    "commit_changes",
    check_more_files,
    {
        "next": "next_file",
        "done": "cleanup"
    }
)
```

**Key Design Decision:** Use LangGraph's StateGraph for state management and error recovery, not custom state machine.

---

### 2. Git Worktree Sandbox Strategy

**Source:** `ideas/git_flow.md`

#### Critical Requirements

**MUST use git worktrees for isolated execution:**

```bash
# Create sandbox from HEAD with new branch
git worktree add /tmp/stomper/sbx_T123 -b sbx/T123 HEAD

# Work happens in isolated sandbox
cd /tmp/stomper/sbx_T123
# AI agent makes changes here

# Extract diff (app controls merge, NOT agent)
git diff HEAD > /tmp/results/T123.patch

# Cleanup
git worktree remove /tmp/stomper/sbx_T123 --force
git branch -D sbx/T123
```

#### Key Insights from Documentation

From `ideas/git_flow.md` conversation:

> **"Agent never touches your codebase directly. You control the merge/push. The agent only produces diffs, nothing else."**

**Safety Rules:**
1. ✅ Every sandbox = new branch + ephemeral worktree
2. ✅ App only consumes diffs (.patch files)
3. ✅ App is the only entity allowed to push — never the agent
4. ✅ Cleanup removes both worktree and branch so nothing leaks

**Why This Matters:**
> "Even if the agent 'destroys the codebase' in its sandbox, your main repo is completely safe. Worst case: you get a garbage .patch file, and you just throw it away."

---

### 3. Technology Stack Requirements

**Source:** `.agent-os/product/tech-stack.md`

#### AI Agent Integration (Task 6 Focus)

**Required Technologies:**
- ✅ **Cursor CLI** - Primary AI agent via headless mode
- ✅ **LangChain** - Tool integration and agent orchestration
- ✅ **LangGraph** - State machine for complex workflows
- ✅ **OpenAI API** - Multi-provider AI support (future)
- ✅ **Anthropic Claude** - Alternative agent support (future)

#### Architecture Patterns

**MUST follow these patterns:**
1. **State Management** - File-level processing state
2. **Error tracking and resolution history**
3. **Rollback and recovery mechanisms**
4. **Async processing** - Sequential processing (MVP), parallel (future)

---

### 4. CLI Interface Requirements

**Source:** `.agent-os/product/cli-design.md`

#### Required CLI Options for Task 6

```python
@app.command()
def fix(
    # Quality tool flags
    ruff: bool = typer.Option(True, "--ruff/--no-ruff"),
    mypy: bool = typer.Option(True, "--mypy/--no-mypy"),
    drill_sergeant: bool = typer.Option(False, "--drill-sergeant/--no-drill-sergeant"),
    
    # AI agent options (TASK 6 FOCUS)
    agent: str = typer.Option("cursor-cli", "--agent", help="AI agent to use"),
    max_retries: int = typer.Option(3, "--max-retries", help="Maximum retry attempts per file"),
    
    # Execution options (TASK 6 FOCUS)
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fixed"),
    parallel: bool = typer.Option(False, "--parallel", help="Process files in parallel"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
)
```

#### Processing Strategies (Required)

```python
class ProcessingStrategy(str, Enum):
    ONE_ERROR_TYPE = "one_error_type"      # Fix one error type at a time
    ONE_ERROR_PER_FILE = "one_error_per_file"  # Fix one error per file
    BATCH_ERRORS = "batch_errors"          # Fix multiple errors up to limit
    ALL_ERRORS = "all_errors"             # Fix all errors in file
```

**Default:** `BATCH_ERRORS` with `max_errors_per_iteration = 5`

---

### 5. Workflow Architecture

**Source:** `.agent-os/product/architecture.md`

#### Core Workflow (MUST follow exactly)

```
1. Quality Assessment → 2. Auto-Fix → 3. AI Agent Fix → 4. Test Validation → 5. Git Commit
```

#### Error Collection Flow

1. Run quality tools with JSON output
2. Parse error results into structured data
3. Group errors by file and type
4. Load advice from error mapping files
5. Generate AI prompts with context

#### Prompt Structure (Required)

```
Fix the following issues in {file}:

{error_descriptions}

Error-specific advice:
{error_advice}

Context:
- File: {file}
- Error count: {count}
- Auto-fixable: {auto_fixable_errors}

Please fix these issues while maintaining:
- Code functionality
- Test compatibility
- Style consistency
```

---

### 6. Git Integration Requirements

**Source:** `.agent-os/product/architecture.md`

#### Branch Strategy

- Session branch: `stomper/auto-fixes-{timestamp}`
- Atomic commits per file
- Conventional commit messages
- Rollback capabilities

#### Commit Message Format (REQUIRED)

```
fix(quality): resolve linting issues in auth.py

- E501: Split long lines using parentheses
- F401: Remove unused imports
- F841: Remove unused variables

Fixed by: stomper v0.1.0
```

**Format:** Conventional Commits standard

---

### 7. Configuration System

**Source:** `.agent-os/product/cli-design.md`

#### Configuration Priority (MUST respect)

1. `stomper.toml` (project root) - Dedicated stomper configuration
2. `pyproject.toml` → `[tool.stomper]` - Integrated with project config
3. Default configuration - Built-in defaults

#### Example Configuration

```toml
[tool.stomper]
ai_agent = "cursor-cli"
max_retries = 3
parallel_files = 1
dry_run = false

[tool.stomper.processing]
max_errors_per_iteration = 5
max_error_types_per_iteration = 2
enable_auto_fix = true

[tool.stomper.git]
branch_prefix = "stomper"
commit_style = "conventional"
auto_commit = true
```

---

### 8. Component Integration

**Source:** `.agent-os/specs/.../technical-spec.md`

#### Components to Integrate (All from Tasks 1-5)

```
Task 6 Orchestrator
    ├── AgentManager (Task 1) - Agent selection & fallback
    ├── CursorClient (Task 2) - AI agent execution  
    ├── PromptGenerator (Task 3) - Adaptive prompt creation
    ├── FixApplier (Task 4) - Apply & validate fixes
    ├── ErrorMapper (Task 5) - Learning & adaptation
    ├── SandboxManager (NEW) - Git worktree management
    └── QualityToolManager (Existing) - Run quality tools
```

#### Integration Pattern

All components **MUST** be initialized with:
- `project_root: Path` - For context
- `mapper: ErrorMapper | None` - For adaptive learning
- Proper error handling and logging

---

### 9. Error Handling Requirements

**Source:** `.agent-os/product/langgraph-workflow.md`

#### Retry Logic (REQUIRED)

```python
async def retry_current_file(state: StomperState) -> StomperState:
    """Retry processing with updated strategy."""
    current_file = state["files"][state["current_file_index"]]
    
    current_file["attempts"] += 1
    current_file["status"] = ProcessingStatus.RETRYING
    
    # Update prompt with feedback from previous attempt
    if current_file["last_error"]:
        feedback = f"Previous attempt failed: {current_file['last_error']}"
        # Incorporate feedback into next prompt
    
    return state
```

**Maximum Retries:** 3 (configurable)

#### Error Recovery

```python
async def handle_processing_error(state: StomperState) -> StomperState:
    """Handle errors that can't be resolved."""
    current_file = state["files"][state["current_file_index"]]
    
    # Log the failure
    state["failed_fixes"].append(current_file["file_path"])
    
    # Decide whether to continue with other files
    if should_abort_on_error(state):
        state["should_continue"] = False
    else:
        # Move to next file
        state = await move_to_next_file(state)
    
    return state
```

---

### 10. Validation Pipeline

**Source:** `.agent-os/specs/.../technical-spec.md`

#### Required Validation Steps

1. **Pre-fix Validation** - Check file state and error details
2. **Fix Application** - Apply AI-generated changes to source files
3. **Post-fix Validation** - Run quality tools to verify fixes
4. **Test Validation** - Run tests to ensure no regressions
5. **Rollback** - Revert changes if validation fails

**Critical:** Tests **MUST** pass before committing

---

### 11. Logging and Observability

**Source:** User preferences + `.agent-os/product/tech-stack.md`

#### Required Logging

**MUST use Rich library for colored output:**

```python
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
```

#### Logging Levels

- **DEBUG** - Detailed state transitions, component calls
- **INFO** - Workflow progress, file processing
- **WARNING** - Retry attempts, fallback strategies
- **ERROR** - Processing failures, validation errors

---

### 12. Success Metrics

**Source:** `.agent-os/product/mission.md`

#### Required Success Criteria

The workflow **MUST** achieve:

- ✅ 80% reduction in time spent on code quality fixes
- ✅ 95% success rate in automated fixes without breaking tests
- ✅ Support for 5+ quality tools by v1.0
- ✅ Positive developer adoption and feedback

#### Session Results (MUST display)

```python
print(f"Successfully fixed {final_state['total_errors_fixed']} errors")
print(f"Processed {len(final_state['successful_fixes'])} files")
if final_state["failed_fixes"]:
    print(f"Failed to fix {len(final_state['failed_fixes'])} files")
```

---

## 🔑 Critical Design Decisions

### Decision 1: LangGraph Over Custom State Machine

**Source:** `.agent-os/product/decisions.md` (DEC-002)

**Rationale:**
- Built-in state persistence and recovery
- Proven error handling patterns
- Easy to visualize and debug
- Extensible for future features

### Decision 2: Git Worktree Isolation

**Source:** `ideas/git_flow.md`

**Rationale:**
- Prevents agent from damaging main codebase
- Allows safe experimentation
- Easy rollback if needed
- Diffs are reviewable

### Decision 3: Test Validation Required

**Source:** `.agent-os/product/architecture.md`

**Rationale:**
- Prevents breaking changes
- Maintains code integrity
- Builds developer trust
- Enables automated rollback

### Decision 4: Conventional Commits

**Source:** `.agent-os/product/architecture.md`

**Rationale:**
- Standardized commit messages
- Better git history
- Automation-friendly
- Industry best practice

---

## 📋 Implementation Checklist

Based on all documentation reviewed:

### Core Workflow ✅

- [ ] Use LangGraph StateGraph exactly as specified
- [ ] Implement all 10 required nodes
- [ ] Add all conditional edges
- [ ] Use StomperState TypedDict structure
- [ ] Integrate all Task 1-5 components

### Git Integration ✅

- [ ] Use git worktrees for sandboxes
- [ ] Create ephemeral branches (sbx/session-id)
- [ ] Extract diffs (not auto-push)
- [ ] Cleanup worktrees and branches
- [ ] Generate conventional commits

### CLI Integration ✅

- [ ] Add --agent, --max-retries options
- [ ] Support --dry-run mode
- [ ] Implement --verbose logging
- [ ] Support --sandbox/--no-sandbox
- [ ] Display rich formatted results

### Error Handling ✅

- [ ] Retry logic (max 3 attempts)
- [ ] Intelligent fallback strategies
- [ ] Graceful error recovery
- [ ] Continue on single file failure
- [ ] Comprehensive logging

### Validation ✅

- [ ] Pre-fix validation
- [ ] Post-fix verification
- [ ] Test execution
- [ ] Rollback on test failure
- [ ] Report validation results

### Configuration ✅

- [ ] Support stomper.toml
- [ ] Support pyproject.toml
- [ ] Respect configuration priority
- [ ] Allow CLI overrides

---

## 🎯 Final Notes

### What Makes Task 6 Different

Task 6 is **NOT just integration** - it's the **complete orchestration layer** that:

1. **Coordinates** all components (Tasks 1-5)
2. **Manages state** through complex workflows
3. **Ensures safety** via sandbox isolation
4. **Validates quality** through test execution
5. **Enables learning** through adaptive strategies
6. **Provides UX** through rich CLI output

### Key Success Factors

1. **Follow LangGraph patterns** - Don't reinvent state management
2. **Trust git worktrees** - Use them as primary safety mechanism
3. **Validate aggressively** - Run tests, verify fixes
4. **Log comprehensively** - Users need to see what's happening
5. **Handle errors gracefully** - Retry, fallback, continue

### Dependencies on Previous Tasks

- **Task 1 (AIAgent):** Protocol for agent swapping
- **Task 2 (CursorClient):** AI fix generation
- **Task 3 (PromptGenerator):** Adaptive prompting
- **Task 4 (FixApplier):** Apply and validate fixes
- **Task 5 (ErrorMapper):** Learning and adaptation

**All must work together in the workflow! 🎯**

---

## 📚 Reference Documentation

For complete details, see:

- Implementation Plan: `task-6-implementation-plan.md`
- LangGraph Design: `.agent-os/product/langgraph-workflow.md`
- Architecture: `.agent-os/product/architecture.md`
- CLI Design: `.agent-os/product/cli-design.md`
- Git Strategy: `ideas/git_flow.md`

**This document serves as the single source of truth for Task 6 requirements derived from all project documentation.** ✨

