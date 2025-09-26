# 🧹 Code Cleanup & Quality Enforcement

## Overview

Analyze errors reported by static analysis tools (`ruff`, `mypy`, etc.), then clean up the code to eliminate findings while preserving functionality.

<pre_flight_check>
INPUT: JSON list of error objects from code quality tools
VALIDATE: Ensure JSON is parseable and complete
</pre_flight_check>

<process_flow>

<step number="1" name="analyze_errors">  

### Step 1: Analyze Errors

Parse the provided JSON error list and categorize issues by tool.

<analysis_areas>
<ruff_errors>
- Unused imports
- Style violations
- Auto-fixable findings
</ruff_errors>
<mypy_errors>
- Type mismatches
- Return type conflicts
- Assignment incompatibilities
</mypy_errors>
</analysis_areas>

<instructions>  
  ACTION: Read JSON error objects carefully  
  CATEGORIZE: Group by tool and auto_fixable flag  
  NOTE: Severity, code, and line numbers for each error  
</instructions>  

</step>  

<step number="2" name="apply_auto_fixes">  

### Step 2: Apply Auto-Fixes

Resolve any issue where `auto_fixable=true`.

<fixing_rules>
* Remove unused imports (e.g., `F401`)
* Apply formatting corrections
* Eliminate duplicate or redundant code patterns
</fixing_rules>

<instructions>  
  ACTION: Apply each auto-fix deterministically  
  ENSURE: Resulting code compiles  
</instructions>  

</step>  

<step number="3" name="resolve_type_issues">  

### Step 3: Resolve Type Issues

Fix errors flagged by `mypy` that are not auto-fixable.

<fixing_rules>
* Correct operand mismatches (e.g., convert `int` → `str` before concatenation)
* Align function return types with type hints
* Adjust function arguments to match defaults (`None` vs `str`)
</fixing_rules>

<instructions>  
  ACTION: Rewrite code so mypy passes cleanly  
  AVOID: Using `# type: ignore`  
  ADD: Type hints where missing or unclear  
</instructions>  

</step>  

<step number="4" name="final_cleanup">  

### Step 4: Final Cleanup

Ensure the code is production-ready and passes all checks.

<verification>  
  - [ ] `ruff` passes without errors  
  - [ ] `mypy` passes without errors  
  - [ ] Code logic preserved  
  - [ ] PEP8 style enforced  
</verification>  

<instructions>  
  ACTION: Provide corrected full file(s)  
  SUMMARY: List of changes applied  
</instructions>  

</step>  

</process_flow>

<post_flight_check>
OUTPUT: Clean, working code with explanation of fixes
</post_flight_check>

