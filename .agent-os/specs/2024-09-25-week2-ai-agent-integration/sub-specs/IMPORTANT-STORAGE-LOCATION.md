# ⚠️ CRITICAL: Storage Location for Error Mapper

## The Problem

Stomper uses **ephemeral git worktree sandboxes** for AI agent execution. These sandboxes:
- Are created in `/tmp/stomper/sbx_*`
- Are **cleaned up** after each run
- Are **NOT persistent**

## The Solution

**Learning data MUST be stored in the MAIN project root, NOT the sandbox!**

### ✅ CORRECT Usage

```python
from pathlib import Path
from stomper.ai.mapper import ErrorMapper
from stomper.ai.sandbox_manager import SandboxManager

# Main project root (where your actual codebase lives)
main_project_root = Path("/home/user/myproject")

# ✅ Create mapper with MAIN project root
mapper = ErrorMapper(project_root=main_project_root)
# Stores to: /home/user/myproject/.stomper/learning_data.json

# Create sandbox for AI agent
sandbox_manager = SandboxManager(project_root=main_project_root)
sandbox_path, branch = sandbox_manager.create_sandbox()
# Creates: /tmp/stomper/sbx_abc123/

# AI agent works in sandbox, mapper records outcomes
# Learning data is saved to MAIN project, NOT sandbox

# After cleanup, learning data persists!
sandbox_manager.cleanup_sandbox(sandbox_path, branch)
# Sandbox deleted, but learning data remains in main project
```

### ❌ WRONG Usage

```python
# ❌ DON'T create mapper with sandbox path!
sandbox_path = Path("/tmp/stomper/sbx_abc123")
mapper = ErrorMapper(project_root=sandbox_path)
# Stores to: /tmp/stomper/sbx_abc123/.stomper/learning_data.json
# THIS WILL BE DELETED when sandbox is cleaned up! ❌
```

## Why This Matters

1. **Persistence:** Learning must survive across sandbox runs
2. **Improvement:** System gets smarter over time with accumulated data
3. **Project-specific:** Patterns are specific to YOUR codebase
4. **Isolation:** Each project learns independently

## Architecture Diagram

```
Main Project: /home/user/myproject/
├── src/
├── tests/
├── .git/
└── .stomper/                          ✅ PERSISTENT
    └── learning_data.json             ✅ Survives cleanup

Sandbox: /tmp/stomper/sbx_abc123/      ⚠️ EPHEMERAL
├── src/                               (copy of main)
├── tests/                             (copy of main)
└── .git/                              (worktree)
    └── [NO .stomper/ HERE!]           ❌ Would be lost!
```

## Git Configuration (Optional)

You can **choose** whether to commit learning data:

### Option A: Commit Learning Data (Default)

**Don't add to `.gitignore`** - commit `.stomper/learning_data.json`

**Benefits:**
- ✅ Team shares learned patterns
- ✅ Consistent fix strategies across developers
- ✅ Faster learning on fresh clones
- ✅ Historical record of what works

**Tradeoffs:**
- ⚠️ May include some environment-specific patterns
- ⚠️ Could have merge conflicts (rare, JSON file)

### Option B: Keep Learning Data Local

Add to `.gitignore`:

```gitignore
# Stomper learning data (keep local)
.stomper/
```

**Benefits:**
- ✅ Each developer learns independently
- ✅ No shared state in version control
- ✅ No merge conflicts

**Tradeoffs:**
- ⚠️ Slower learning on each machine
- ⚠️ Lost on fresh clones
- ⚠️ Similar to `.venv/` or `__pycache__/`

### Recommendation

**Start by committing** `.stomper/` to benefit from shared learning. If you notice environment-specific issues, add it to `.gitignore` later.

## Testing Verification

The test suite includes a specific test to prevent this mistake:

```python
def test_storage_in_main_project_not_sandbox(tmp_path):
    """Test that storage is in main project root, not sandbox."""
    main_project = tmp_path / "main"
    sandbox_path = tmp_path / "sandbox"
    main_project.mkdir()
    sandbox_path.mkdir()
    
    # Mapper should use main project, not sandbox
    mapper = ErrorMapper(project_root=main_project)
    assert mapper.storage_path.is_relative_to(main_project)
    assert not mapper.storage_path.is_relative_to(sandbox_path)
```

## Summary

**Golden Rule:** Always pass `main_project_root` to `ErrorMapper`, never `sandbox_path`!

✅ `ErrorMapper(project_root=main_project_root)`  
❌ `ErrorMapper(project_root=sandbox_path)`

