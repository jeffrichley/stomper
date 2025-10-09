# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2024-09-25-week2-ai-agent-integration/spec.md

> Created: 2024-09-25
> Status: Ready for Implementation

## Tasks

- [x] 1. Swappable AI Agent Protocol
  - [x] 1.1 Write tests for AIAgent protocol
  - [x] 1.2 Implement abstract AIAgent base class
  - [x] 1.3 Add agent selection and configuration
  - [x] 1.4 Add agent metadata and capabilities tracking
  - [x] 1.5 Add fallback strategy for multiple agents
  - [x] 1.6 Verify all tests pass

- [x] 2. Cursor CLI Headless Integration
  - [x] 2.1 Write tests for CursorClient class
  - [x] 2.2 Implement CursorClient with cursor-cli execution
  - [x] 2.3 Add prompt validation and sanitization
  - [x] 2.4 Add response parsing and validation
  - [x] 2.5 Add error handling for cursor-cli failures
  - [x] 2.6 Verify all tests pass

- [x] 3. Error-to-Prompt Generation System
  - [x] 3.1 Write tests for PromptGenerator class
  - [x] 3.2 Implement error context extraction
  - [x] 3.3 Implement prompt template generation
  - [x] 3.4 Add code context inclusion in prompts
  - [x] 3.5 Add prompt size optimization
  - [x] 3.6 Verify all tests pass

- [x] 4. Fix Application and Validation Pipeline
  - [x] 4.1 Write tests for FixApplier class
  - [x] 4.2 Implement fix application to source files
  - [x] 4.3 Add file backup and restoration
  - [x] 4.4 Implement fix validation pipeline
  - [x] 4.5 Add rollback functionality
  - [x] 4.6 Verify all tests pass

- [x] 5. Error Mapping and Learning System
  - [x] 5.1 Write tests for Mapper class
  - [x] 5.2 Implement error pattern tracking
  - [x] 5.3 Add success rate calculation
  - [x] 5.4 Implement adaptive prompting
  - [x] 5.5 Add fallback strategy selection
  - [x] 5.6 Verify all tests pass

- [x] 6. AI Agent Workflow Integration (LangGraph Orchestration) - **PHASE 1 COMPLETE** ✅
  - [x] 6.1 Write integration tests for complete workflow
    - [x] Test full end-to-end workflow (initialize → collect → process → verify → test → commit → cleanup)
    - [x] Test error handling and retry logic
    - [x] Test git worktree sandbox isolation
    - [x] Test adaptive learning integration
  - [x] 6.2 Create LangGraph workflow orchestrator
    - [x] Define workflow state in `workflow/state.py` (StomperState, FileState, ErrorInfo, ProcessingStatus)
    - [x] Implement `workflow/orchestrator.py` with LangGraph StateGraph
    - [x] Implement all workflow nodes (initialize, collect_errors, process_file, verify_fixes, run_tests, commit_changes, next_file, cleanup, handle_error, retry_file)
    - [x] Define conditional edges and transitions
    - [x] Integrate ErrorMapper, AgentManager, PromptGenerator, FixApplier components
  - [x] 6.3 Add AI agent options to CLI configuration
    - [x] Add workflow options to CLI `fix` command (--sandbox/--no-sandbox, --test/--no-test, --max-retries, --strategy, --agent)
    - [x] Update `config/models.py` with WorkflowConfig
    - [x] Implement workflow result display with rich tables
    - [x] Wire orchestrator into CLI
  - [x] 6.4 Implement end-to-end error fixing workflow
    - [x] Update `SandboxManager` with git worktree support
    - [x] Implement sandbox creation, cleanup, and diff extraction
    - [x] Test sandbox isolation (changes don't affect main workspace)
    - [x] Verify workflow runs in both sandbox and direct modes
  - [x] 6.5 Add comprehensive error handling and logging
    - [x] Create `workflow/logging.py` with rich logging configuration
    - [x] Add try/except to all workflow nodes
    - [x] Implement error recovery strategies
    - [x] Add optional log file output
  - [x] 6.6 Verify all tests pass and workflow works end-to-end
    - [x] Run complete test suite (`just test`)
    - [x] Manual testing on real project
    - [x] Verify sandbox creation/cleanup
    - [x] Verify AI agent integration
    - [x] Verify stats command shows learning
    - [x] Verify all CLI options work correctly
  - [x] **6.7 REFACTOR: Per-File Worktree Architecture** ✅
    - [x] Refactor from session-level worktree to per-file worktree
    - [x] Add new state fields and nodes (create_worktree, generate_prompt, call_agent, extract_diff, apply_to_main, commit_in_main, destroy_worktree)
    - [x] Update all existing nodes for new architecture
    - [x] Rebuild graph structure with new edges
    - [x] All tests passing (273+ tests) ✅
    - [x] Documentation complete ✅
  
- [ ] **PHASE 2: Parallel File Processing** 🚀 (READY TO START)
  - [ ] Implementation prompt created: `PHASE-2-PARALLEL-PROCESSING-PROMPT.md`
  - [ ] Working demos created and verified:
    - [ ] `demo_langgraph_complete_pattern.py` - Complete pattern with all 4 features
    - [ ] `demo_langgraph_builtin_concurrency.py` - Built-in max_concurrency
    - [ ] `demo_langgraph_parallel.py` - Manual approach (educational)
  - [ ] Documentation created:
    - [ ] `STOMPER-PARALLEL-IMPLEMENTATION-GUIDE.md` - Implementation guide
    - [ ] `FINAL-PARALLEL-SUMMARY.md` - Complete overview
    - [ ] `LANGGRAPH-CONCURRENCY-GUIDE.md` - Technical deep dive
    - [ ] `PARALLEL-PROCESSING-FAQ.md` - Questions and answers
