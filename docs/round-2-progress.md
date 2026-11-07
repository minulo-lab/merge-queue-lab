# Round 2: progress so far (work in progress, 2026-11-05)

Round 2 stopped early. This file records what was done and found, so the next
session can pick up from here. Nothing in the repository's protection was changed.

## Phase 0 (done)

- The `LAB_ADMIN_TOKEN` secret still authenticates: `apply-config.yml` with
  `model=show` ([run 41989397721](https://github.com/minulo-lab/merge-queue-lab/actions/runs/41989397721))
  read both rulesets. Write access is untested.
- The live configuration matches the baseline (squash only; `main-merge-queue`
  id 25550677 and `signed-commits` id 25543744 active; queue SQUASH, ALLGREEN,
  build 5, group 1–5, wait 0, timeout 10).
- Open PRs: #9, #10, #13, #14, #17 (bot scenarios B2–B4), #23 (S3), #26–#28 (S7),
  #30 (S9), #33 (S11), #34 (S6a), #36 (S4), #37, #38, #47, #48 (S10).
  #10 is not cited in `scenarios.md`; its body says `after_open: auto-merge-delete-branch`,
  so it is probably an earlier B4 attempt.
- [Lab] #30 is the only PR with an "added to merge queue" event and no removal
  (REST timeline and GraphQL agree). It is now `dirty` (merge conflict).
  Renovate's #50–#52 merged through the queue afterwards, and each group was built
  on `main`'s tip, not behind #30. Decision on dequeuing #30: still open.
- Leftover queue branches `gh-readonly-queue/main/pr-30-e651ff9…` and
  `pr-31-0b42890…` are the orphaned S9 groups. Every `lab/*` and `bot/*` branch
  belongs to an open PR.

## A finding that may correct round 1

[Docs: REST OpenAPI description v1.1.4, read 2026-11-05]
`GET /repos/{owner}/{repo}/pulls/{n}/merge-async/{uuid}` returns `merged`,
`enqueued` or `failed`, and a `failed` result "includes a message describing the
failure". Results are kept for 24 hours. Round 1 saved UUIDs but never polled
them, so README finding 3 ("silently dropped") is unverified. Proposed scenario
S30: repeat S7's direct merges, S11's early enqueue and a conflicting enqueue
with `scripts/lab.py poll`.

## Facts checked for later scenarios (read 2026-11-05)

- GraphQL: `enqueuePullRequest(input: {pullRequestId, jump, expectedHeadOid})`,
  `dequeuePullRequest(input: {id})`, `repository.mergeQueue(branch:)` with
  `MergeQueueEntry {position, state, enqueuer, jump, solo, baseCommit, headCommit}`.
  REST `merge-async` has no jump or dequeue option.
- `pull_request` has `enqueued` and `dequeued` activity types. The dequeued
  webhook `reason` enum: UNKNOWN_REMOVAL_REASON, MANUAL, MERGE, MERGE_CONFLICT,
  CI_FAILURE, CI_TIMEOUT, ALREADY_MERGED, QUEUE_CLEARED, ROLL_BACK,
  BRANCH_PROTECTIONS, GIT_TREE_INVALID, INVALID_MERGE_COMMIT.
  `merge_group` has `checks_requested` (and a `destroyed` webhook with reason
  merged / invalidated / dequeued).
- Docs: build concurrency 0 stops new `checks_requested` dispatches; "jumping …
  will cause a full rebuild of all in-progress pull requests"; the docs say the
  queue can't be removed from with the CLI.
- Terraform provider `integrations/github` v6.9.0, `github_repository_ruleset`
  `merge_queue` defaults: `merge_method` MERGE, `check_response_timeout_minutes` 60,
  `min_entries_to_merge_wait_minutes` 5. Import: `terraform import github_repository_ruleset.x repo:ID`.
- `gh pr merge` source: `--admin` skips the queue (`shouldAddToMergeQueue` is
  `mergeQueueRequired && !UseAdmin`); `--delete-branch` is refused with a queue.

## Environment limits met in this session

- GraphQL is blocked from the session's `gh`, so queue list, dequeue and jump
  must run in a workflow (planned: `.github/workflows/queue-ops.yml`, not written yet).
  A jump made with `GITHUB_TOKEN` will probably get no `merge_group` CI (see B3),
  so jump needs another token or a click in the UI.
- `docs.github.com`, `github.blog`, `docs.renovatebot.com` and
  `registry.terraform.io` were blocked; docs were read from their source files on
  `raw.githubusercontent.com`. Terraform 1.17.1 and the provider zip downloaded
  fine, so S12 can use a filesystem mirror.

## Tooling started (this branch, untested against GitHub)

`scripts/lab.py` gains: `apply queue --max-group --merge-method --allowed-methods
--thread-resolution`, `apply settings --methods`, `open lanes --fail N --draft`,
and the commands `push`, `close`, `reopen`, `delete-branch`, `review`,
`comment-thread`, `status`, `poll` and `queue` (the last one needs
`queue-ops.yml`, which still has to be written). `apply-config.yml` inputs are
not updated yet.

## Not started

Phase 1 workflows, every Phase 2 scenario (S12–S30, B6–B10) and Phase 3.
