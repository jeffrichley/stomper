---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	initialize(initialize)
	collect_errors(collect_errors)
	create_worktree(create_worktree)
	generate_prompt(generate_prompt)
	call_agent(call_agent)
	verify_fixes(verify_fixes)
	run_tests(run_tests)
	extract_diff(extract_diff)
	apply_to_main(apply_to_main)
	commit_in_main(commit_in_main)
	destroy_worktree(destroy_worktree)
	next_file(next_file)
	aggregate_results(aggregate_results)
	cleanup(cleanup)
	handle_error(handle_error)
	destroy_worktree_on_error(destroy_worktree_on_error)
	retry_file(retry_file)
	__end__([<p>__end__</p>]):::last
	__start__ --> initialize;
	aggregate_results --> cleanup;
	apply_to_main --> commit_in_main;
	call_agent --> verify_fixes;
	collect_errors -. &nbsp;no_files&nbsp; .-> aggregate_results;
	collect_errors -. &nbsp;has_files&nbsp; .-> create_worktree;
	commit_in_main --> destroy_worktree;
	create_worktree --> generate_prompt;
	destroy_worktree -. &nbsp;done&nbsp; .-> aggregate_results;
	destroy_worktree -. &nbsp;next&nbsp; .-> next_file;
	destroy_worktree_on_error -. &nbsp;continue&nbsp; .-> next_file;
	extract_diff --> apply_to_main;
	generate_prompt --> call_agent;
	handle_error --> destroy_worktree_on_error;
	initialize --> collect_errors;
	next_file --> create_worktree;
	retry_file --> generate_prompt;
	run_tests -. &nbsp;pass&nbsp; .-> extract_diff;
	run_tests -. &nbsp;fail&nbsp; .-> handle_error;
	verify_fixes -.-> aggregate_results;
	verify_fixes -. &nbsp;abort&nbsp; .-> handle_error;
	verify_fixes -. &nbsp;retry&nbsp; .-> retry_file;
	verify_fixes -. &nbsp;success&nbsp; .-> run_tests;
	cleanup --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
