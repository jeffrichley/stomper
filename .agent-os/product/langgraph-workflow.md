# LangGraph State Machine Design

## Workflow Overview

LangGraph will orchestrate the complex multi-step workflow with state management, error handling, and retry logic.

## State Definition

```python
from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class ErrorInfo(TypedDict):
    tool: str
    code: str
    message: str
    file_path: str
    line_number: int
    auto_fixable: bool

class FileState(TypedDict):
    file_path: str
    status: ProcessingStatus
    errors: List[ErrorInfo]
    fixed_errors: List[ErrorInfo]
    attempts: int
    max_attempts: int
    last_error: Optional[str]

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

## Graph Definition

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

def create_stomper_workflow():
    """Create the LangGraph workflow for stomper."""
    
    workflow = StateGraph(StomperState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_session)
    workflow.add_node("collect_errors", collect_all_errors)
    workflow.add_node("process_file", process_current_file)
    workflow.add_node("verify_fixes", verify_file_fixes)
    workflow.add_node("run_tests", run_test_suite)
    workflow.add_node("commit_changes", commit_file_changes)
    workflow.add_node("next_file", move_to_next_file)
    workflow.add_node("cleanup", cleanup_session)
    workflow.add_node("handle_error", handle_processing_error)
    workflow.add_node("retry_file", retry_current_file)
    
    # Add edges
    workflow.add_edge("initialize", "collect_errors")
    workflow.add_edge("collect_errors", "process_file")
    workflow.add_edge("process_file", "verify_fixes")
    
    # Conditional edges
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
    
    workflow.add_edge("next_file", "process_file")
    workflow.add_edge("cleanup", END)
    workflow.add_edge("handle_error", END)
    
    return workflow.compile()
```

## Node Implementations

### Initialize Session
```python
async def initialize_session(state: StomperState) -> StomperState:
    """Initialize the stomper session."""
    from datetime import datetime
    
    session_id = f"stomper-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    branch_name = f"stomper/auto-fixes-{session_id}"
    
    # Create git branch
    create_git_branch(branch_name)
    
    state.update({
        "session_id": session_id,
        "branch_name": branch_name,
        "current_file_index": 0,
        "should_continue": True,
        "successful_fixes": [],
        "failed_fixes": [],
        "total_errors_fixed": 0
    })
    
    return state
```

### Collect All Errors
```python
async def collect_all_errors(state: StomperState) -> StomperState:
    """Collect errors from all enabled quality tools."""
    files = []
    
    # Get all Python files to process
    python_files = find_python_files()
    
    for file_path in python_files:
        file_errors = []
        
        # Run each enabled tool
        for tool in state["enabled_tools"]:
            errors = run_quality_tool(tool, file_path)
            file_errors.extend(errors)
        
        if file_errors:  # Only add files with errors
            files.append({
                "file_path": str(file_path),
                "status": ProcessingStatus.PENDING,
                "errors": file_errors,
                "fixed_errors": [],
                "attempts": 0,
                "max_attempts": 3
            })
    
    state["files"] = files
    return state
```

### Process Current File
```python
async def process_current_file(state: StomperState) -> StomperState:
    """Process the current file with AI agent."""
    current_file = state["files"][state["current_file_index"]]
    file_path = current_file["file_path"]
    
    # Update status
    current_file["status"] = ProcessingStatus.IN_PROGRESS
    
    try:
        # Apply auto-fixes first
        auto_fixed = apply_auto_fixes(file_path, current_file["errors"])
        if auto_fixed:
            # Re-collect errors after auto-fix
            current_file["errors"] = collect_errors_for_file(file_path)
        
        # Generate AI prompt for remaining errors
        if current_file["errors"]:
            prompt = build_ai_prompt(file_path, current_file["errors"])
            
            # Call AI agent
            fixed_content = await call_ai_agent(prompt, state["ai_agent"])
            
            # Write fixed content
            write_fixed_content(file_path, fixed_content)
        
        current_file["status"] = ProcessingStatus.COMPLETED
        
    except Exception as e:
        current_file["status"] = ProcessingStatus.FAILED
        current_file["last_error"] = str(e)
    
    return state
```

### Verify Fixes
```python
async def verify_fixes(state: StomperState) -> StomperState:
    """Verify that fixes actually resolved the errors."""
    current_file = state["files"][state["current_file_index"]]
    file_path = current_file["file_path"]
    
    # Re-run quality tools to check if errors are resolved
    new_errors = collect_errors_for_file(file_path)
    
    # Check which errors were actually fixed
    original_errors = set(current_file["errors"])
    remaining_errors = set(new_errors)
    fixed_errors = original_errors - remaining_errors
    
    if fixed_errors:
        current_file["fixed_errors"].extend(fixed_errors)
        state["total_errors_fixed"] += len(fixed_errors)
    
    # Update remaining errors
    current_file["errors"] = list(remaining_errors)
    
    return state

def should_retry_fixes(state: StomperState) -> str:
    """Decide whether to retry fixes or continue."""
    current_file = state["files"][state["current_file_index"]]
    
    if current_file["errors"] and current_file["attempts"] < current_file["max_attempts"]:
        return "retry"
    elif current_file["errors"]:
        return "abort"  # Max attempts reached
    else:
        return "success"  # All errors fixed
```

### Run Tests
```python
async def run_test_suite(state: StomperState) -> StomperState:
    """Run the test suite to ensure fixes don't break functionality."""
    try:
        result = run_pytest()
        if result.returncode == 0:
            return state
        else:
            state["error_message"] = f"Tests failed: {result.stderr}"
            return state
    except Exception as e:
        state["error_message"] = f"Test execution error: {str(e)}"
        return state

def check_test_results(state: StomperState) -> str:
    """Check if tests passed."""
    return "pass" if not state.get("error_message") else "fail"
```

### Commit Changes
```python
async def commit_changes(state: StomperState) -> StomperState:
    """Commit the fixed file to git."""
    current_file = state["files"][state["current_file_index"]]
    file_path = current_file["file_path"]
    
    # Generate commit message
    commit_message = generate_commit_message(file_path, current_file["fixed_errors"])
    
    # Create commit
    create_git_commit(commit_message, [file_path])
    
    # Track successful fix
    state["successful_fixes"].append(file_path)
    
    return state
```

## Error Handling and Retry Logic

### Retry File Processing
```python
async def retry_current_file(state: StomperState) -> StomperState:
    """Retry processing the current file with updated strategy."""
    current_file = state["files"][state["current_file_index"]]
    
    current_file["attempts"] += 1
    current_file["status"] = ProcessingStatus.RETRYING
    
    # Update prompt with feedback from previous attempt
    if current_file["last_error"]:
        feedback = f"Previous attempt failed: {current_file['last_error']}"
        # Incorporate feedback into next prompt
    
    return state
```

### Handle Processing Error
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

## Usage with LangGraph

```python
from langgraph.graph import StateGraph

async def run_stomper_workflow(config: StomperConfig):
    """Run the complete stomper workflow."""
    
    # Create the workflow
    workflow = create_stomper_workflow()
    
    # Initial state
    initial_state = {
        "enabled_tools": config.enabled_tools,
        "processing_strategy": config.processing_strategy,
        "max_errors_per_iteration": config.max_errors_per_iteration,
        "ai_agent": config.ai_agent
    }
    
    # Run the workflow
    final_state = await workflow.ainvoke(initial_state)
    
    # Process results
    print(f"Successfully fixed {final_state['total_errors_fixed']} errors")
    print(f"Processed {len(final_state['successful_fixes'])} files")
    
    if final_state["failed_fixes"]:
        print(f"Failed to fix {len(final_state['failed_fixes'])} files")
    
    return final_state
```

## Benefits of LangGraph Integration

1. **State Management**: Automatic state persistence and recovery
2. **Error Handling**: Built-in retry logic and error recovery
3. **Parallel Processing**: Easy to add parallel file processing
4. **Observability**: Built-in logging and monitoring
5. **Extensibility**: Easy to add new nodes and workflows
6. **Testing**: Each node can be tested independently
7. **Visualization**: Graph structure can be visualized
