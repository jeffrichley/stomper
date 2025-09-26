# 🧹 Code Cleanup & Quality Enforcement (v2)

## Overview
Analyze and fix findings from **Ruff** and **Mypy** while preserving behavior and enforcing project standards.

<pre_flight_check>
INPUT: Raw error data from quality tools (JSON array)

```json
[
  {
    "tool": "ruff",
    "file": "demo.py",
    "line": 1,
    "column": 0,
    "code": "E501",
    "message": "Line too long (120 > 88 characters)",
    "severity": "error",
    "auto_fixable": true
  },
  {
    "tool": "ruff",
    "file": "demo.py",
    "line": 5,
    "column": 0,
    "code": "F401",
    "message": "'os' imported but unused",
    "severity": "error",
    "auto_fixable": true
  },
  {
    "tool": "mypy",
    "file": "demo.py",
    "line": 10,
    "column": 0,
    "code": "missing-return-type",
    "message": "Function is missing a return type annotation",
    "severity": "error",
    "auto_fixable": false
  }]

CONFIRM:
- Use this JSON as the source of truth for errors.
- Do not alter or reformat the JSON itself.
- All fixes should correspond to these entries.

ASSUMPTIONS:
Code context may be supplied for review,  
but all changes must be applied directly in the git worktree  
to the files listed in the error JSON.

</pre_flight_check>

<process_flow>

<step number="1" name="analyze_errors">
### Step 1: Analyze Errors

<analysis_areas>
**Ruff Errors:**
- demo.py:1:0 — E501 — Line too long (120 > 88 characters)
- demo.py:5:0 — F401 — 'os' imported but unused

**Mypy Errors:**
- demo.py:10:0 — missing-return-type — Function is missing a return type annotation
**Totals:**Ruff = 2 (auto-fixable = 2),Mypy = 1 (auto-fixable = 0)</analysis_areas>

<instructions>
ACTION: Build a change plan mapping each error to one concrete fix.
OUTPUT: A clear list of which issues go to Step 2 (auto-fix) vs Step 3 (manual).
</instructions>



<step number="2" name="apply_auto_fixes">
### Step 2: Apply Auto-Fixes

<fixing_rules>

</fixing_rules>

<instructions>
ACTION: Apply deterministic auto-fixes without altering behavior.
ENSURE: Code compiles after changes.
</instructions>
</step>




<step number="3" name="resolve_manual_fixes">
### Step 3: Resolve Manual Fixes

<fixing_rules>

</fixing_rules>

<instructions>
ACTION: Rewrite code to resolve these findings while preserving logic.
AVOID: Using # type: ignore.
ADD: Type hints or code adjustments as required.
</instructions>
</step>




<step number="4" name="final_verification">
### Step 4: Final Verification

<verification>
- [ ] Ruff passes with no findings
- [ ] Mypy passes with no errors
- [ ] All tests green (no regressions)
- [ ] Code style compliant (max line length 88)
</verification>

<instructions>
ACTION: Confirm all checks pass and summarize changes made.
OUTPUT: Full corrected files + bullet summary of fixes.
</instructions>
</step>



</process_flow>

<post_flight_check>
OUTPUT: Clean, working code with explanation of fixes
</post_flight_check>

## Code Context

_Code context is available in the git worktree. Apply fixes directly to the files listed in the error JSON._

## Error-Specific Advice

### Line too long (E501)

Split long lines using parentheses or backslashes.

#### Examples:
- Use parentheses for function calls
- Extract complex expressions to variables
- Use string concatenation for long strings

#### Fix Strategy:
- Break long lines at logical points (commas, operators)
- Use parentheses for function calls and expressions
- Extract complex expressions to intermediate variables
- Use string concatenation or f-strings for long strings


### Imported but unused (F401)

Remove unused imports to clean up the code.

#### Examples:
- Remove unused import statements
- Remove unused from imports
- Keep only necessary imports

#### Fix Strategy:
- Remove the entire import line if all imports are unused
- Remove specific items from from-import statements
- Check if imports are used in comments or docstrings
- Consider if imports are needed for type hints


Fix missing-return-type: Function is missing a return type annotation



## Requirements

1. Fix all listed issues
2. Maintain existing functionality  
3. Follow project coding standards
4. Preserve test compatibility
