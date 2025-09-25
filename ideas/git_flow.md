what it says...
git worktree add ../sandboxes/sbx_T123_feature -b sbx/T123 origin/main
does that actually mean origin/main or whatever branch im on?

should the sandbox be ephemeral too? like a tmp directory that is only available while my app is running?

do you have to make a new branch to make a new worktree?


ChatGPT said:

Great set of questions, Jeff — let’s unpack each one carefully so you know exactly how Git worktrees behave and how best to use them for your sandbox design.

1. Does git worktree add … -b sbx/T123 origin/main actually mean origin/main or “whatever branch I’m on”?

It literally means “create a new worktree starting from origin/main”.

If you specify origin/main, Git will use the tip of that branch as the base.

If you wanted “whatever branch I’m currently on,” you’d pass HEAD instead:

git worktree add ../sandbox HEAD


So:

origin/main = always based on main branch from remote.

HEAD = based on your current checkout.

<branchname> = based on that branch tip.

👉 For “don’t surprise me” consistency, most teams start from a stable known branch (origin/main) instead of “whatever I happen to be on.” That way, every sandbox is predictable.

2. Should the sandbox be ephemeral too (tmp dir only while app is running)?

Yes — that’s the ideal design.

Worktrees are cheap and disposable, so it makes sense to treat them as ephemeral sandboxes:

Create in a tmp directory (e.g., /tmp/stomper-sbx-uuid/).

Let the agent do its work.

Collect diffs.

Tear it down immediately after.

This keeps your workspace clean and avoids stale sandboxes cluttering your repo. If you want reviewable runs, you can export patches (git diff > patchfile.patch) instead of keeping the sandbox around.

3. Do you have to make a new branch to make a new worktree?

Not strictly, but it’s usually the right choice.

Option A: Without -b (no new branch)

git worktree add ../sandbox HEAD


Creates a new checkout of your current branch.

If you commit inside the sandbox, it affects the same branch as your main checkout.

Risk: easy to accidentally overlap with your “real” dev branch.

Option B: With -b (new branch) ✅ recommended

git worktree add ../sandbox -b sbx/T123 origin/main


Creates a dedicated branch (sbx/T123).

Changes/commits stay isolated.

Easy to delete branch + worktree when you’re done.

👉 For a sandbox system, always create a new branch. That way, the sandbox has its own isolated branch, and cleanup is trivial (git worktree remove + git branch -D).

🔑 Best Practice for Your App

Always start from a predictable base (usually origin/main).

Place worktrees in a tmp sandbox dir so they’re ephemeral.

Use -b to make a new branch per sandbox → ensures no overlap.

After collecting diffs, destroy worktree + branch and keep only the patch.

✅ Example command for your manager app:

git fetch origin
git worktree add /tmp/stomper/sbx_T123 -b sbx/T123 origin/main


Cleanup:

git worktree remove /tmp/stomper/sbx_T123 --force
git branch -D sbx/T123


Do you want me to sketch a Mermaid flow diagram showing the full lifecycle (create → agent edits → collect diff → cleanup) so you can drop it into your docs?

You said:
llets rework your spec now. should we default the tree coming from HEAD? this is the flow, i make a branch, write a bunch of code, set off the agent to clean it up, push up to git

sounds like making a new branch is the right way, but then my app needs to manage deleting it too, right?


ChatGPT said:

Perfect — let’s refine the spec with your real workflow in mind. You’re right: the flow you described changes how the sandbox should be created and managed.

🌳 Revised Worktree Sandbox Spec
🎯 Goals

Support your developer flow:

You create a branch and write some code.

You hand that branch off to the agent for cleanup/refinement.

The agent works in a sandbox (so your working dir stays untouched).

Results are collected and pushed back.

Ensure safety (no surprises to main or your working copy).

Automate branch + worktree cleanup when the sandbox is discarded.

🧩 Workflow
1. Developer Creates a Branch

You do:

git checkout -b feature/my-new-thing
# ...write some code...


Now you’re on feature/my-new-thing. This is the branch you want the agent to clean up.

2. App Creates an Ephemeral Worktree from HEAD

App does:

git worktree add /tmp/stomper/sbx_T123 HEAD


HEAD means: use your current branch (feature/my-new-thing).

Creates a sandbox directory (/tmp/stomper/sbx_T123) with its own working copy of the branch.

Both your main checkout and the sandbox point to the same branch, but changes in the sandbox don’t clutter your current working dir.

3. Agent Runs Inside Sandbox

App points Cursor CLI at sandbox dir:

cd /tmp/stomper/sbx_T123
cursor-cli run "Clean up and refactor code"


Agent edits files, commits if needed. You can enforce commit discipline or let it just modify files.

4. Collect Results

App inspects sandbox:

git -C /tmp/stomper/sbx_T123 diff HEAD~1
# or just: git -C /tmp/stomper/sbx_T123 status


If the agent committed, you can just push that branch:

git -C /tmp/stomper/sbx_T123 push origin feature/my-new-thing


If the agent only edited files without committing, you can capture a patch:

git -C /tmp/stomper/sbx_T123 diff > cleanup.patch

5. Cleanup

Once results are harvested:

git worktree remove /tmp/stomper/sbx_T123 --force


⚠️ Note: Since the sandbox shares the same branch (feature/my-new-thing), you do not delete the branch — you only remove the sandbox. The branch remains in your repo (with any agent commits, if pushed).

🔑 Why This Flow Is Right for You

Start from HEAD → matches your flow (“I already have a feature branch”).

No duplicate branch → avoids confusion (sandbox is just another checkout of the same branch).

Ephemeral directory → sandbox is auto-cleaned, your workspace stays clean.

Branch persists → you keep your work + agent changes, then push to remote.

🛡️ Branch/Worktree Management Rules

If sandbox is based on HEAD (your branch) → cleanup = remove worktree only.

If sandbox is based on origin/main (new sbx/branch) → cleanup = remove worktree + delete sbx branch.

👉 Since your flow is developer branch → agent cleanup → push branch, the first model (HEAD-based sandbox) is cleaner. You don’t need to delete the branch — just the sandbox dir.

✅ Revised Command Set for Your App

Create sandbox from current branch (HEAD):

git worktree add /tmp/stomper/sbx_T123 HEAD


Run agent in sandbox:

cd /tmp/stomper/sbx_T123
cursor-cli run "Refactor code"


Collect results (optional patch):

git -C /tmp/stomper/sbx_T123 diff > /tmp/results/T123.patch


Push results (if agent committed):

git -C /tmp/stomper/sbx_T123 push origin feature/my-new-thing


Cleanup sandbox:

git worktree remove /tmp/stomper/sbx_T123 --force


⚡️ So yes:

Default base = HEAD (since you’re already on the feature branch).

Make a new branch? → No, not needed here.

Should app delete branch? → No, because the branch is the artifact you push. Just delete the worktree dir.

Do you want me to also spec out the alternative flow (starting from origin/main into a new sbx branch) side by side, so you can switch between “developer-driven cleanup” and “agent-created experiments”?

You said:
im confused. lets say it doesnt make a new branch and it destroys the codebase somehow and then pushes. thats bad right?

i want to never actually use the codebase or whatever the agent pushes. my app will manage the diff and pushing.
ChatGPT said:

Exactly, Jeff — you’ve nailed the concern. If you let the agent “live” on the same branch you’re actively developing on, there’s always a risk:

The agent could commit garbage directly to your feature branch.

If your app naively pushes it, you’ve polluted the branch (and possibly remote).

Worst case: you or the CI pull down broken code.

That’s why for a “never trust the agent directly” rule, the sandbox needs to be truly isolated:

✅ Safer Sandbox Spec (Agent Edits → Diff → App Push)
1. Always create a new temporary branch

Start from a stable base (origin/main or your current branch HEAD),

but never give the agent your real branch.

git fetch origin
git worktree add /tmp/stomper/sbx_T123 -b sbx/T123 HEAD


Creates a branch sbx/T123 from whatever you’re currently on.

The agent works only inside /tmp/stomper/sbx_T123.

2. Agent edits in sandbox only

The agent can git add / git commit all it wants inside the worktree.

Those commits are isolated to sbx/T123.

Your real feature branch stays untouched.

3. App collects the diff

Instead of pushing the agent’s branch, the app extracts diffs:

git -C /tmp/stomper/sbx_T123 diff origin/main > /tmp/results/T123.patch


or, if based on HEAD:

git -C /tmp/stomper/sbx_T123 diff HEAD > /tmp/results/T123.patch


Your app now has a clean, reviewable patch file.

That patch is the only artifact you trust from the agent.

4. App applies the diff on your behalf

You decide where to apply it:

Onto your real feature branch:

git apply /tmp/results/T123.patch


Or into a staging branch for review.

Then you commit and push under your control, not the agent’s.

5. Cleanup

Destroy the sandbox worktree and temporary branch:

git worktree remove /tmp/stomper/sbx_T123 --force
git branch -D sbx/T123

🔑 Why This is Safer

Agent never touches your codebase directly.

You control the merge/push. The agent only produces diffs, nothing else.

Ephemeral by design. Sandboxes and temp branches vanish once you’re done.

🛡️ Rules for Your App

Every sandbox = new branch + ephemeral worktree.

The app only consumes diffs (.patch files).

The app is the only entity allowed to push — never the agent.

Cleanup removes both worktree and branch so nothing leaks.

✅ This way, even if the agent “destroys the codebase” in its sandbox, your main repo is completely safe. Worst case: you get a garbage .patch file, and you just throw it away.

Would you like me to give you a Mermaid diagram showing this “safe flow” (developer branch → sandbox branch → agent edits → diff → apply → push) so it’s crystal clear in your docs?