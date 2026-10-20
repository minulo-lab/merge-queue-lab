# Scenarios

Each scenario states its question, the exact setup, what the documentation
predicts, and what this repository observed, with links to the pull requests
and workflow runs. Raw measurements are in [results/](results/).

Shared setup for every scenario:

- Repository settings (`scripts/lab.py apply settings`): squash merges only,
  auto-merge allowed, head branches deleted after merge.
- `scripts/lab.py apply signed-commits`: signatures required on every branch
  except `gh-pages`.
- Required check: **Required checks** from `ci.yml`, pinned to the GitHub Actions
  app. Approvals: 0, except in B1.

Approvals are set to 0 for the human-path scenarios because a PR author cannot
approve their own PR, and the queue checks approvals before a PR enters it, not
inside the queue. B1 uses 1 approval to exercise bot approval.

Labels: **[Docs]** = GitHub documentation predicts it · **[Lab]** = observed here.

---

<a id="s0"></a>
## S0: loose protection lets a semantic conflict break `main`

- **Question.** With required checks but *without* strict mode or a queue, can
  two individually green PRs break `main`?
- **Setup.** `scripts/lab.py apply loose`
- **Steps.** `scripts/lab.py open conflict --tag s0`. Wait until both are green,
  then merge PR A (rename), then PR B (a new caller of the old name). B's checks
  are still green from before A landed.
- **Prediction.** `main` turns red after B. GitHub never re-tests B against the
  new `main`. [Docs: about protected branches, "loose" required checks]
- **Observed.** _running_

<a id="s1"></a>
## S1: strict mode, 4 independent PRs

- **Setup.** `scripts/lab.py apply classic`, which means strict, `enforce_admins`,
  and signatures on `main`.
- **Steps.** `scripts/lab.py open lanes --n 4 --tag s1`, then
  `scripts/lab.py land strict <PRs> --label s1-strict`. The script merges the first
  green PR, then for each next PR: update branch, wait for CI, merge.
- **Prediction.** About N−1 = 3 branch updates and N = 4 CI cycles in series.
- **Observed.** _running_

<a id="s2"></a>
## S2: merge queue, 4 independent PRs

- **Setup.** `scripts/lab.py apply queue --timeout 10`. This is a ruleset on
  `main` with: PR required, squash only, Required checks with strict policy, and
  a merge queue (SQUASH, ALLGREEN, build concurrency 5, group size 1–5, no wait,
  10-minute check timeout).
- **Steps.** `scripts/lab.py open lanes --n 4 --tag s2`, then
  `scripts/lab.py land queue <PRs> --label s2-queue`. That enqueues all four
  through the async merge API with `merge_action: merge_queue`.
- **Prediction.** All four groups build in parallel and land in about one CI
  cycle. [Docs: managing a merge queue]
- **Observed.** _running_

<a id="s3"></a>
## S3: the queue catches a semantic conflict

- **Steps.** Under the S2 setup: `scripts/lab.py open conflict --tag s3`, then
  enqueue A then B.
- **Prediction.** Group A passes. Group B (main + A + B) fails at import time, so
  B is removed and `main` stays green.
- **Observed.** _running_

<a id="s4"></a>
## S4: a required check whose workflow lacks `merge_group`

- **Setup.** `scripts/lab.py apply queue --timeout 10 --require "Changelog fragment (PR only)"`
- **Steps.** Open one lane PR and enqueue it.
- **Prediction.** The check passes on the PR, so the PR can enter the queue. In
  the group the check never reports, so the PR is removed after the 10-minute
  timeout. [Docs: "The merge will fail as the required status check will not be
  reported."]
- **Observed.** _running_

<a id="s5"></a>
## S5: signatures required on every branch, plus a queue

- **Setup.** The `signed-commits` ruleset (`~ALL` except `gh-pages`) stays active
  during S2 and S3.
- **Question.** Can the queue create its `gh-readonly-queue/*` branches and land
  commits? Is the squash commit on `main` verified?
- **Prediction.** Undocumented. GitHub signs squash merges it creates, but the
  docs say nothing about queue branches or merge-group commits.
- **Observed.** _running_

<a id="s6"></a>
## S6: a pull-request-shaped check inside a merge group

- **Setup A.** `--require "Changelog fragment (naive)"`. The job runs on
  `merge_group` and diffs `pull_request.base.sha..head.sha`, which are empty
  there.
- **Setup B.** `--require "Changelog fragment (queue-safe)"`. The job has
  `if: github.event_name == 'pull_request'`.
- **Prediction.** A: the group fails, so the PR is removed. B: the job is skipped
  in the group, a skipped job reports success, so the PR merges. [Docs: status
  checks]
- **Observed.** _running_

<a id="s7"></a>
## S7: direct merges and bypass on a queue branch

- **Steps.** With the queue ruleset active (empty bypass list), on an open green
  PR: `scripts/lab.py probe rest-merge <PR>`, `probe async-direct`,
  `probe async-direct-bypass`, `probe update-branch`. The caller is a repository
  admin and organization owner.
- **Prediction.** The REST merge endpoint "does not support … merging with a
  merge queue". `direct_merge` with `bypass_rules` only works for actors allowed
  to bypass. [Docs: REST pulls; async merge API]
- **Observed.** _running_

<a id="s8"></a>
## S8: strict mode and a queue together

- **Question.** With `strict_required_status_checks_policy: true` *and* a merge
  queue, must a PR that is behind `main` be updated before it can be enqueued?
- **Prediction.** Undocumented.
- **Observed.** _running_

<a id="s9"></a>
## S9: the queue's ruleset is deleted and recreated while PRs wait

- **Why.** Some configuration-as-code setups delete and recreate every ruleset on
  each apply.
- **Steps.** Enqueue two PRs, delete the ruleset, recreate it from
  `config/ruleset-main-merge-queue.json`, and watch the PRs' timelines.
- **Prediction.** Undocumented. The `pull_request.dequeued` webhook's reason enum
  includes `QUEUE_CLEARED`.
- **Observed.** _running_

<a id="b1"></a>
## B1: Renovate PR, with bot approval, platform auto-merge and the queue

- **Setup.** Queue ruleset with `--approvals 1`. Renovate app installed;
  `renovate.json` has `automerge: true`. `bot-approve.yml` approves Renovate PRs
  as `github-actions[bot]`.
- **Prediction.** Renovate turns on auto-merge, the bot approval satisfies the
  review rule, and GitHub enqueues the PR when requirements pass.
  [Docs: Renovate automerge, "GitHub merge queue"]
- **Observed.** _running_

<a id="b2"></a>
## B2: a PR opened with `GITHUB_TOKEN`

- **Steps.** Run the **Bot PR (GITHUB_TOKEN)** workflow with
  `commit_via=api, after_open=nothing`.
- **Prediction.** Since 2026-06-11, its `pull_request` runs start in an
  approval-required state. [Docs: GITHUB_TOKEN]
- **Observed.** _running_

<a id="b3"></a>
## B3: `GITHUB_TOKEN` turns on auto-merge

- **Steps.** Bot PR with `after_open=auto-merge`.
- **Prediction.** "The built-in `GITHUB_TOKEN` cannot add pull requests to the
  queue." [Docs: automating Dependabot with GitHub Actions]
- **Observed.** _running_

<a id="b4"></a>
## B4: `gh pr merge --auto --delete-branch` on a queue branch

- **Steps.** Bot PR with `after_open=auto-merge-delete-branch`.
- **Prediction.** gh refuses `--delete-branch` when the base requires a queue.
  The refusal comes from the CLI source (`pkg/cmd/pr/merge/merge.go`), since
  v2.64.0.
- **Observed.** _running_

<a id="b5"></a>
## B5: a bot pushes an unsigned commit

- **Steps.** Bot PR with `commit_via=git`.
- **Prediction.** The push to the new branch is rejected by the signed-commits
  ruleset.
- **Observed.** _running_
