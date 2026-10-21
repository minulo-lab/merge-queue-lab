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

How the runs were driven, on 2026-10-21 (all times UTC):

- Scenario branches and their commits came from the `prepare-branches.yml`
  workflow, so GitHub signed them. The pull requests were opened, enqueued and
  merged by the organization's owner through `scripts/lab.py`, using a GitHub App
  user token (REST only).
- Unless a scenario says otherwise, PRs were enqueued with the async merge API
  (`merge_action: merge_queue`) once their own checks had passed.
- Protection models were switched with the `apply-config.yml` workflow.
- Times in "landing time" run from the first enqueue or merge call to the last
  merge, so they leave out the PRs' own CI.

Why a PR left the queue: the REST timeline only says *that* it was removed.
GitHub's own reason (`merge_conflict`, `failed_checks`, `checks_timed_out`,
`branch_protection_failure`, `merged`) comes from GraphQL; the
`inspect-queue.yml` workflow collected them in
[results/queue-removal-reasons.md](results/queue-removal-reasons.md).

Labels: **[Docs]** = GitHub documentation predicts it · **[Lab]** = observed here ·
**[Inference]** = a conclusion from the two.

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
- **Observed.** [Lab] Loose protection: required checks, but neither strict mode
  nor a queue. [#43](https://github.com/minulo-lab/merge-queue-lab/pull/43) (PR A,
  rename) and [#44](https://github.com/minulo-lab/merge-queue-lab/pull/44) (PR B,
  new caller of the old name) were both green. A merged at 15:47:03 UTC and B at
  15:47:12. GitHub did not re-test B against the new `main`; B's green checks were
  from 15:46:28, before A landed. The `push` run on `main` for B's commit
  `31df079` failed in **Unit tests**
  ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/39628833108)).
- `main` stayed red until a fix-forward PR,
  [#45](https://github.com/minulo-lab/merge-queue-lab/pull/45), merged at 15:54:03:
  7 minutes, and every PR opened from `main` in that window would have inherited the
  failure. Strict mode (S1) or a queue (S3) would have stopped B before it merged.

<a id="s1"></a>
## S1: strict mode, 4 independent PRs

- **Setup.** `scripts/lab.py apply classic`, which means strict, `enforce_admins`,
  and signatures on `main`.
- **Steps.** `scripts/lab.py open lanes --n 4 --tag s1`, then
  `scripts/lab.py land strict <PRs> --label s1-strict`. The script merges the first
  green PR, then for each next PR: update branch, wait for CI, merge.
- **Prediction.** About N−1 = 3 branch updates and N = 4 CI cycles in series.
- **Observed.** [Lab] [#39](https://github.com/minulo-lab/merge-queue-lab/pull/39),
  [#40](https://github.com/minulo-lab/merge-queue-lab/pull/40),
  [#41](https://github.com/minulo-lab/merge-queue-lab/pull/41) and
  [#42](https://github.com/minulo-lab/merge-queue-lab/pull/42). The script played
  a perfectly attentive human. It merged #39 at 15:35:44 UTC. Each next PR was then
  `behind`, so the script pressed **Update branch**, waited for CI, and merged:
  #40 at 15:37:54, #41 at 15:40:35, #42 at 15:43:15.
- **Landing time: 7.6 minutes. 7 `CI` runs** (4 on the PRs, 3 after branch
  updates), **3 branch updates**, 16.9 runner-minutes
  ([results/s1-strict.json](results/s1-strict.json)).
- Compared with S2: the queue landed the same four PRs **2.8× faster** (2.7 vs 7.6
  minutes), with one more CI run (8 vs 7) and about the same runner time (18.8 vs
  16.9 minutes), and nobody had to come back three times to press "Update branch".
  Strict mode's gap grows with every extra PR and with every minute a person
  takes to notice their PR is behind.
- One glitch, unrelated to either model: #40's **Required checks** check run stayed
  `in_progress` for 8 minutes after its job had finished. Re-running the workflow
  cleared it. It happened before landing started, so it doesn't affect the numbers.

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
- **Observed.** [Lab] [#18](https://github.com/minulo-lab/merge-queue-lab/pull/18),
  [#19](https://github.com/minulo-lab/merge-queue-lab/pull/19),
  [#20](https://github.com/minulo-lab/merge-queue-lab/pull/20) and
  [#21](https://github.com/minulo-lab/merge-queue-lab/pull/21) were enqueued
  within three seconds of each other at 13:14:30 UTC. GitHub built four groups at
  once, each on top of the one before: `pr-18` on `main`, `pr-19` on `pr-18`'s
  commit, and so on. All four group runs passed by 13:16:49. At 13:17:12 `main`
  fast-forwarded to the last group's commit, and all four PRs show that same merge
  time. The four commits on `main` are exactly the four tested group commits.
- **Landing time: 2.7 minutes**, about one CI cycle. **8 `CI` runs** (4 on the PRs,
  4 in the queue), no branch updates, 18.8 runner-minutes
  ([results/s2-queue.json](results/s2-queue.json)).

<a id="s3"></a>
## S3: the queue catches a semantic conflict

- **Steps.** Under the S2 setup: `scripts/lab.py open conflict --tag s3`, then
  enqueue A then B.
- **Prediction.** Group A passes. Group B (main + A + B) fails at import time, so
  B is removed and `main` stays green.
- **Observed.** [Lab] [#22](https://github.com/minulo-lab/merge-queue-lab/pull/22)
  (rename) and [#23](https://github.com/minulo-lab/merge-queue-lab/pull/23) (new
  caller of the old name) were both green on their own. They were enqueued one
  second apart. Group `pr-22` (`main` + #22) passed. Group `pr-23` (`pr-22`'s
  commit + #23) failed in **Unit tests**: the new module imports a name that no
  longer exists. Lint passed, because the import is only resolved when the code
  runs. At 13:23:42 UTC the queue removed #23; a second later it merged #22.
  `main` never contained the broken combination.
- 4 `CI` runs, 2.6 minutes from enqueue to the merge
  ([results/s3-queue.json](results/s3-queue.json)). #23 stays open, and its own
  PR checks are still green, which is exactly why strict-less protection would
  have let it in (see S0).

<a id="s4"></a>
## S4: a required check whose workflow lacks `merge_group`

- **Setup.** `scripts/lab.py apply queue --timeout 5 --require "Changelog fragment (PR only)"`
- **Steps.** Open one lane PR and enqueue it.
- **Prediction.** The check passes on the PR, so the PR can enter the queue. In
  the group the check never reports, so the PR is removed after the
  timeout. [Docs: "The merge will fail as the required status check will not be
  reported."]
- **Observed.** [Lab] Run with a 5-minute check timeout instead of 10, to save
  time. [#36](https://github.com/minulo-lab/merge-queue-lab/pull/36): on the PR,
  **Changelog fragment (PR only)** passed, so the PR could enter the queue (14:46:58
  UTC). In the group, `CI` passed at 14:49:10, but the PR-only workflow has no
  `merge_group` trigger, so that required check never reported. At 14:52:29, five
  and a half minutes after it entered, the queue removed the PR. B3's #17 shows the
  wording GitHub uses for this: "removed this pull request from the merge queue
  due to no response for status checks".
- The PR looked fully green the whole time. Nothing on the PR warns that one of
  its required checks can't run in the queue; the cost is one timeout per attempt.

<a id="s5"></a>
## S5: signatures required on every branch, plus a queue

- **Setup.** The `signed-commits` ruleset (`~ALL` except `gh-pages`) stays active
  during S2 and S3.
- **Question.** Can the queue create its `gh-readonly-queue/*` branches and land
  commits? Is the squash commit on `main` verified?
- **Prediction.** Undocumented. GitHub signs squash merges it creates, but the
  docs say nothing about queue branches or merge-group commits.
- **Observed.** [Lab] The signed-commits ruleset was active in B1 and every queue
  scenario. The queue created its `gh-readonly-queue/main/pr-<n>-<sha>` branches
  and merged normally. The commit a group tests *is* the commit that lands.
  Group `pr-5-59533e2…` tested `490b558`, and `490b558` is #5's commit on `main`.
  The same holds for #4 (`ec77867`) and #6 (`14588cf`). Every commit the queue
  put on `main` shows `verified: true`, reason `valid`, committer `GitHub`.
- **[Inference]** With squash merges, the PR's own commits never reach the queue
  branch or `main`, only the squash commit GitHub creates. So unsigned commits on
  a PR branch would not trip the rule there.
- A side effect of "the tested commit is the commit that lands": `ci.yml` also runs
  on `push` to `main`, so every queue merge was tested twice with the same SHA. For
  example `e8d555f` (#35) has a `merge_group` run and then a `push` run. With a
  queue, a test-only workflow on `push` to `main` is a duplicate. Release or
  publish jobs on `push` are a different matter and still belong there.

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
- **Observed.** [Lab]
  - **A, naive check required.**
    [#34](https://github.com/minulo-lab/merge-queue-lab/pull/34): on the PR both
    required checks passed. In its group, **Changelog fragment (naive)** failed
    after 4 seconds (`git diff` with empty base and head SHAs). The queue removed
    the PR at 14:36:59 UTC, 49 seconds after it was enqueued, while the group's
    `CI` run was still going. A failed required check ends the attempt at once.
  - **B, queue-safe check required.**
    [#35](https://github.com/minulo-lab/merge-queue-lab/pull/35): in its group the
    check reported **skipped**, `Required checks` passed, and the PR merged at
    14:43:28. A skipped job satisfied the required check. (The naive variant also
    ran in that group and failed, but it wasn't required in B.)
- The bot exemption `if: github.event.pull_request.user.type != 'Bot'` does not
  protect anyone in a group. There is no `pull_request` object, so the condition
  is true for every PR, human or bot. B1 shows it: the naive check failed in every
  Renovate group.

<a id="s7"></a>
## S7: direct merges and bypass on a queue branch

- **Steps.** With the queue ruleset active (empty bypass list), on four open
  green PRs, one call each: `scripts/lab.py probe rest-merge <PR>`,
  `probe async-direct`, `probe async-direct-bypass`, and `probe async-queue` as the
  control. The caller is a repository admin and organization owner.
- **Prediction.** The REST merge endpoint "does not support … merging with a
  merge queue". `direct_merge` with `bypass_rules` only works for actors allowed
  to bypass. [Docs: REST pulls; async merge API]
- **Observed.** [Lab] Four green PRs, one path each, called by the organization
  owner through a GitHub App user token. The queue ruleset's bypass list is empty.

  | PR | Call | GitHub's answer | What happened |
  | --- | --- | --- | --- |
  | [#26](https://github.com/minulo-lab/merge-queue-lab/pull/26) | `PUT /pulls/26/merge` (squash) | HTTP 405: "Repository rule violations found. Changes must be made through the merge queue" | Nothing; PR open |
  | [#27](https://github.com/minulo-lab/merge-queue-lab/pull/27) | `PUT /pulls/27/merge-async`, `merge_action: direct_merge` | `"status": "pending"`, "Merge request enqueued." | Nothing after 4 minutes; PR open |
  | [#28](https://github.com/minulo-lab/merge-queue-lab/pull/28) | same, plus `bypass_rules: true` | same `pending` answer | Nothing; PR open |
  | [#29](https://github.com/minulo-lab/merge-queue-lab/pull/29) | `PUT /pulls/29/merge-async`, `merge_action: merge_queue` (control) | same `pending` answer | Queued in 2 seconds, merged 2.6 minutes later |

- The old merge endpoint fails loudly with a clear message. The async endpoint
  accepts every request and then does nothing visible when the merge isn't
  allowed, so a script that trusts its answer will think it merged. Check the PR
  (or its timeline) afterwards. With an empty bypass list, even an owner can't skip
  the queue through the API.

<a id="s8"></a>
## S8: strict mode and a queue together

- **Question.** With `strict_required_status_checks_policy: true` *and* a merge
  queue, must a PR that is behind `main` be updated before it can be enqueued?
- **Prediction.** Undocumented.
- **Observed.** [Lab] The queue ruleset keeps
  `strict_required_status_checks_policy: true` in every queue scenario.
  [#24](https://github.com/minulo-lab/merge-queue-lab/pull/24) merged through the
  queue at 13:30:01 UTC, which left
  [#25](https://github.com/minulo-lab/merge-queue-lab/pull/25) one commit behind
  `main` (compare API: `behind_by: 1`). #25 was enqueued as it was, entered the
  queue a second later, and merged at 13:33:14. Its branch was never updated, and
  its group was built on the new `main`. B1 saw the same with auto-merge: #4 was
  one commit behind when it was enqueued, and it merged without an update.
- So with a queue, the strict setting costs nothing extra: nobody has to click
  "Update branch" before enqueueing ([results/s8-strict-plus-queue.json](results/s8-strict-plus-queue.json)).

<a id="s9"></a>
## S9: the queue's ruleset is deleted and recreated while PRs wait

- **Why.** Some configuration-as-code setups delete and recreate every ruleset on
  each apply.
- **Steps.** Enqueue two PRs, delete the ruleset, recreate it from
  `config/ruleset-main-merge-queue.json`, and watch the PRs' timelines.
- **Prediction.** Undocumented. The `pull_request.dequeued` webhook's reason enum
  includes `QUEUE_CLEARED`.
- **Observed.** [Lab] [#30](https://github.com/minulo-lab/merge-queue-lab/pull/30)
  and [#31](https://github.com/minulo-lab/merge-queue-lab/pull/31) entered the
  queue at 13:44:05 and 13:44:07 UTC, and their groups started CI at 13:44:24. At
  13:44:32 the `apply-config` workflow deleted the queue ruleset and created it
  again from the same JSON (new ruleset id). Both group runs then **passed**, but
  neither PR was merged *or* removed. 18 minutes later both still showed only
  "added to merge queue": no removal event, no timeout, no merge. They were
  stranded.
- The recreated queue itself worked. A new PR,
  [#32](https://github.com/minulo-lab/merge-queue-lab/pull/32), was enqueued at
  14:06:17 and merged at 14:08:54; its group was built straight on `main`, not
  behind the stranded entries.
- Enqueueing a stranded PR again recovers it: #31 got a second "added to merge
  queue" at 14:09:04, a new group, and merged at 14:11:31. (#30 could not be
  retried, because #32 had changed the same file and #30 now had a merge
  conflict. That conflict came from the test setup, not from the queue.)
- So any automation that deletes and recreates rulesets on every apply will
  strand whatever is in the queue at that moment, silently. Update rulesets in
  place, or re-enqueue afterwards ([results/s9-recreate.json](results/s9-recreate.json)).

<a id="s10"></a>
## S10: "Restrict who can push" on top of a queue

- **Why.** Many teams keep classic branch protection with **Restrict who can
  push to matching branches** (for example: maintainers, admins and one
  dependency-bot app). When a queue lands a PR, whose push is it?
- **Setup.** The S2 queue ruleset, plus `scripts/lab.py apply restricted`:
  classic protection whose only setting is **Restrict who can push**.
  - A: `--push-apps renovate`, admins exempt (`enforce_admins: false`).
  - B: the same with `--enforce-admins`, so the account that enqueues (an
    organization owner) is *not* allowed to push.
  - C: `--push-users <the enqueuer> --push-apps renovate --enforce-admins`, so the
    enqueuer is explicitly allowed.
  - D: `--push-apps renovate,github-merge-queue`, admins exempt.
- **Steps.** One lane PR per variant, enqueued with the async merge API.
- **Prediction.** Undocumented. The merge-queue docs do not mention push
  restrictions. In B1 and S2 the queue's merges are credited to the account that
  enqueued (`merged_by`), which suggests that account's push rights are checked.
- **Observed.** [Lab] Four variants, one lane PR each, all enqueued by the
  organization owner. Every group's `CI` passed, and then the queue removed the PR
  without merging. GraphQL gives the reason as `branch_protection_failure`
  (see [results/queue-removal-reasons.md](results/queue-removal-reasons.md)).

  | Variant | Push allowance on `main` | Admins | PR | Result |
  | --- | --- | --- | --- | --- |
  | A | Renovate app only | exempt | [#37](https://github.com/minulo-lab/merge-queue-lab/pull/37) | removed, `branch_protection_failure` |
  | B | Renovate app only | `enforce_admins: true` | [#38](https://github.com/minulo-lab/merge-queue-lab/pull/38) | removed, `branch_protection_failure` |
  | C | Renovate app **and the enqueuing user** | `enforce_admins: true` | [#47](https://github.com/minulo-lab/merge-queue-lab/pull/47) | removed, `branch_protection_failure` |
  | D | Renovate app + `github-merge-queue` requested | exempt | [#48](https://github.com/minulo-lab/merge-queue-lab/pull/48) | removed, `branch_protection_failure` |

- In D, the API accepted `github-merge-queue` in the list of apps but stored only
  Renovate; reading the restrictions back showed one app. So there was no way to
  allow the queue itself.
- **[Inference]** The queue's final push to `main` is not judged by the enqueuer's
  push rights: an admin (A) and an explicitly allowed user (C) both failed. With
  classic "Restrict who can push", a queue can't merge anything. Keep push
  restrictions out of classic protection on a queue branch. Rulesets have a
  "Restrict updates" rule with a bypass list. A community report says the GitHub
  Merge Queue app can be added to a ruleset's bypass list (there, to let it create
  branches under "Restrict creations")
  ([discussion #167530](https://github.com/orgs/community/discussions/167530)).
  This lab did not test that route.

<a id="s11"></a>
## S11: enqueue before the PR's own checks have finished

- **Why.** With one list of required checks for both the PR and the queue, a team
  may want to start the queue run without waiting for the PR run.
- **Steps.** Open one lane PR and, right away, call the async merge API with
  `merge_action: merge_queue`. Watch when the PR enters the queue.
- **Prediction.** The async API docs say only "basic pull request state checks"
  run when the request is made. Whether the request waits for the required checks
  like auto-merge, fails, or enqueues at once is not documented.
- **Observed.** [Lab] [#33](https://github.com/minulo-lab/merge-queue-lab/pull/33)
  was opened at 14:12:43 UTC and enqueued through the async API a second later,
  while its checks were still running. The API answered `"status": "pending"`,
  "Merge request enqueued." The PR's **Required checks** passed at 14:14:39. Ten
  minutes after that it had still never entered the queue: no queue event of any
  kind.
- So the async API does not wait for the PR to become mergeable. A request made
  too early is dropped without a trace. To queue a PR the moment its checks pass,
  turn on auto-merge ("Merge when ready") instead, which is what Renovate does in
  B1. The PR's own run of the required checks has to pass before it can enter
  the queue; the queue then runs them again on the group.

<a id="b1"></a>
## B1: Renovate PR, with bot approval, platform auto-merge and the queue

- **Setup.** Queue ruleset with `--approvals 1`. Renovate app installed;
  `renovate.json` has `automerge: true`. `bot-approve.yml` approves Renovate PRs
  as `github-actions[bot]`.
- **Prediction.** Renovate turns on auto-merge, the bot approval satisfies the
  review rule, and GitHub enqueues the PR when requirements pass.
  [Docs: Renovate automerge, "GitHub merge queue"]
- **Observed.** [Lab] Renovate opened four PRs,
  [#4](https://github.com/minulo-lab/merge-queue-lab/pull/4) (ruff),
  [#5](https://github.com/minulo-lab/merge-queue-lab/pull/5) (actions/checkout),
  [#6](https://github.com/minulo-lab/merge-queue-lab/pull/6) (actions/setup-python) and
  [#7](https://github.com/minulo-lab/merge-queue-lab/pull/7) (pytest), and turned on
  auto-merge (squash) on each. `bot-approve.yml` approved each one as
  `github-actions[bot]` within about 20 seconds, and again after every Renovate
  force-push. When a PR's checks passed, GitHub added it to the queue. The
  timeline credits that to `renovate[bot]`, and the `merge_group` runs ran with
  `renovate[bot]` as actor. All four merged through the queue
  (`merged_by: renovate[bot]`) between 12:09 and 12:18 UTC on 2026-10-21.
- Two of them were thrown out first. #6 left the queue in the same second that #5
  merged, and #7 in the same second that #4 merged, each "due to a conflict with
  the base branch". #5 and #6 change neighbouring lines of `ci.yml`; #4 and #7
  change neighbouring lines of `requirements-dev.txt`. While the PR ahead was
  still queued, no merge group was built for the PR behind it, so no queue CI was
  wasted. Renovate rebased each removed PR within 40 seconds (its PR body says
  "Rebasing: Whenever PR becomes conflicted") and turned auto-merge on again. The
  bot approved again, and the PR went through PR CI and the queue a second time.
- Cost ([results/b1-renovate.json](results/b1-renovate.json)): 14 `CI` runs, 4 of
  them in the queue, about 32 runner-minutes. The two ejections cost one extra PR
  CI run each.

<a id="b2"></a>
## B2: a PR opened with `GITHUB_TOKEN`

- **Steps.** Run the **Bot PR (GITHUB_TOKEN)** workflow with
  `commit_via=api, after_open=nothing`.
- **Prediction.** Since 2026-06-11, its `pull_request` runs start in an
  approval-required state. [Docs: GITHUB_TOKEN]
- **Observed.** [Lab] [#9](https://github.com/minulo-lab/merge-queue-lab/pull/9):
  all four `pull_request` runs (CI, Changelog, Changelog (PR only), Approve bot
  PRs) concluded `action_required`, actor `github-actions[bot]`. The PR page says
  "This workflow requires approval from a maintainer" and offers **Approve
  workflows to run**. The PR's commit, made through the contents API with
  `GITHUB_TOKEN`, is verified (committer GitHub).
- The REST endpoint documented for fork PRs,
  `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`, also approved these
  runs (HTTP 201; it asks for `actions: write`). An approved run then starts with
  `triggering_actor` set to the approver. B3 uses this.

<a id="b3"></a>
## B3: `GITHUB_TOKEN` turns on auto-merge

- **Steps.** Bot PR with `after_open=auto-merge`.
- **Prediction.** "The built-in `GITHUB_TOKEN` cannot add pull requests to the
  queue." [Docs: automating Dependabot with GitHub Actions]
- **Observed.** [Lab] Three ways for `github-actions[bot]` to ask, and none of
  them lands the PR:
  1. **Auto-merge while checks are pending.**
     [#12](https://github.com/minulo-lab/merge-queue-lab/pull/12): `gh pr merge <url> --auto --squash`
     succeeded with the warning "The merge strategy for main is set by the merge
     queue", and the timeline shows auto-merge enabled by `github-actions[bot]`.
     Its runs were approved (B2) and passed. The PR then sat `clean`, with
     auto-merge on, for more than five minutes and was never queued.
     Control: a person enqueued the same PR through the async API. It entered the
     queue within a second and merged normally.
  2. **The async merge API** (`merge_action: merge_queue`), on
     [#13](https://github.com/minulo-lab/merge-queue-lab/pull/13) while its checks
     were pending and on [#17](https://github.com/minulo-lab/merge-queue-lab/pull/17)
     when it was green: both answered `"status": "pending"` with "Merge request
     enqueued.", but no queue event followed. It gave the same answer for #13 after
     #13 had a merge conflict. That response only acknowledges the request; it
     doesn't say the PR can be queued.
  3. **`gh pr merge --auto` on a PR that is already green.** This did put #17 in
     the queue: "github-actions added this pull request to the merge queue"
     (13:00:28 UTC). But GitHub never created a `merge_group` workflow run for its
     group. At 13:11:15 it removed the PR "due to no response for status checks",
     the same failure as [S4](#s4).
- **[Inference]** GitHub documents that events triggered with `GITHUB_TOKEN` don't
  start workflow runs. The merge group's `merge_group` event was triggered by the
  bot's enqueue, so no required check could report.
- So a `GITHUB_TOKEN` bot can open PRs and approve them, but a person, a GitHub
  App installation token or a PAT has to put them in the queue.

<a id="b4"></a>
## B4: `gh pr merge --auto --delete-branch` on a queue branch

- **Steps.** Bot PR with `after_open=auto-merge-delete-branch`.
- **Prediction.** gh refuses `--delete-branch` when the base requires a queue.
  The refusal comes from the CLI source (`pkg/cmd/pr/merge/merge.go`), since
  v2.64.0.
- **Observed.** [Lab] [#14](https://github.com/minulo-lab/merge-queue-lab/pull/14):
  `gh pr merge <url> --auto --squash --delete-branch` printed
  "X Cannot use `-d` or `--delete-branch` when merge queue enabled" and exited
  1. Without `--delete-branch` (B3) gh goes ahead. Head branches are still
  deleted after merge by the repository setting "Automatically delete head
  branches".

<a id="b5"></a>
## B5: a bot pushes an unsigned commit

- **Steps.** Bot PR with `commit_via=git`.
- **Prediction.** The push to the new branch is rejected by the signed-commits
  ruleset.
- **Observed.** [Lab] The push of an unsigned commit to `bot/generated-…` was
  rejected: "GH013: Repository rule violations found … Commits must have verified
  signatures". No PR was opened.
