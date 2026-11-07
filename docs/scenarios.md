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
- Pull requests that stayed open are evidence, not leftovers: each is a PR the
  queue or the API did not merge in its scenario (B2–B4, S3, S4, S6, S7, S9, S10,
  S11).

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
- `main` stayed broken until a fix-forward PR,
  [#45](https://github.com/minulo-lab/merge-queue-lab/pull/45), merged at 15:54:03:
  6 minutes 51 seconds after B. The failing `push` run itself only reported at
  15:50:49, so for the first three and a half minutes nothing even looked wrong.
  Every PR opened from `main` in that window would have inherited the failure. Strict mode (S1) or a queue (S3) would have stopped B before it merged.

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
  on `push` to `main`, so the commit at the tip of each fast-forward was tested
  twice with the same SHA. For example `e8d555f` (#35) has a `merge_group` run and
  then a `push` run. (In S2 four commits landed in one fast-forward, so only the
  tip got a `push` run.) With a
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
    14:43:20. A skipped job satisfied the required check. (The naive variant also
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
  queue at 13:29:51 UTC, which left
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
  queue" at 14:09:04, a new group, and merged at 14:11:31. #30 was enqueued again
  too, and the API answered "pending", but nothing happened: #32 had changed the
  same file, so #30 now had a merge conflict. That conflict came from the test
  setup, not from the queue.
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
- **Observed.** [Lab] Renovate opened six PRs at 12:01–12:02 UTC. Two of them,
  #2 and #3, merged directly at 12:03, before the queue ruleset was applied at
  12:05. The other four,
  [#4](https://github.com/minulo-lab/merge-queue-lab/pull/4) (ruff),
  [#5](https://github.com/minulo-lab/merge-queue-lab/pull/5) (actions/checkout),
  [#6](https://github.com/minulo-lab/merge-queue-lab/pull/6) (actions/setup-python) and
  [#7](https://github.com/minulo-lab/merge-queue-lab/pull/7) (pytest), already had
  auto-merge (squash) turned on and went through the queue. `bot-approve.yml`
  approved each one as `github-actions[bot]` within about 20 seconds, and again
  after five of the seven Renovate force-pushes (the 12:04 pushes to #4 and #7
  started no workflow runs at all). When a PR's checks passed, GitHub added it to
  the queue. The timeline credits that to `renovate[bot]`, and the `merge_group`
  runs ran with `renovate[bot]` as actor. All four merged through the queue
  (`merged_by: renovate[bot]`) between 12:09 and 12:18 UTC on 2026-10-21.
- Two of them were thrown out first. #6 left the queue within a second of #5
  merging, and #7 in the same second that #4 merged, each "due to a conflict with
  the base branch" (GraphQL reason `merge_conflict`). #5 and #6 change neighbouring lines of `ci.yml`; #4 and #7
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
     queue 2 seconds later and merged normally.
  2. **The async merge API** (`merge_action: merge_queue`), on
     [#13](https://github.com/minulo-lab/merge-queue-lab/pull/13) while its checks
     were pending and on [#17](https://github.com/minulo-lab/merge-queue-lab/pull/17)
     when it was green: both answered `"status": "pending"` with "Merge request
     enqueued.", but no queue event followed (for #17 the window was 108 seconds,
     until the next attempt; #13 sat green and mergeable for about ten minutes
     with no queue event, and has had none since). It gave the same answer for #13 after
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

---

# Round 2 (run 2026-11-07)

Round 2 adds the merge-queue interactions round 1 did not test. The shared setup
is the same as above (squash only, signatures on every branch, `Required checks`
required, approvals 0) unless a scenario says otherwise, and the baseline was
restored after every scenario (`apply-config.yml` runs are linked where the
model changed).

What changed in how the lab was driven:

- The lab was driven from a session whose `gh` could use REST but not GraphQL,
  and which could not write repository settings, commit statuses, contents or
  refs directly. So:
  - queue operations without a REST equivalent (list, dequeue, enqueue with
    jump) and a few helpers (bot reviews, commit statuses, head-branch push and
    delete) run in [`queue-ops.yml`](../.github/workflows/queue-ops.yml) as
    `github-actions[bot]`, through `scripts/lab.py queue <op> <PR>`;
  - scenario branches were created with `git push` from that session. Its
    pushes were signed, so the signed-commits ruleset stayed on and the lab's
    own tooling PRs needed no maintenance window ([#54](https://github.com/minulo-lab/merge-queue-lab/pull/54), [#55](https://github.com/minulo-lab/merge-queue-lab/pull/55), [#104](https://github.com/minulo-lab/merge-queue-lab/pull/104), [#113](https://github.com/minulo-lab/merge-queue-lab/pull/113), [#123](https://github.com/minulo-lab/merge-queue-lab/pull/123)).
- Each scenario's lanes write `lanes/<tag>-lane-<i>.txt`, so lanes of different
  scenarios never conflict.
- PRs were enqueued one at a time with `PUT …/merge-async` and the result was
  polled with `GET …/merge-async/{uuid}` until it left `pending` (see S30, which
  explains why).
- Documentation was read from GitHub's docs source
  ([github/docs](https://github.com/github/docs), `main`), the REST OpenAPI
  description (v1.1.4) and the GraphQL schema on 2026-11-05 and 2026-11-07,
  because docs.github.com was not reachable from the session. Quotes below are
  from those files.

Round 1 results that round 2 corrects are flagged in S30 and in the
[README](../README.md#what-the-documentation-didnt-tell-us).

Round 2 pull requests left open, as evidence: #57 (S15, dequeued), #62 (S16,
jumped then timed out), #69 (S30, conflict), #71 and #72 (S12, prepared for the
apply that did not run), #75 and #116 (S22, failed in the queue), #81 (S23),
#97 and #98 (S25, REBASE), #99 (S26, can never enter), #108 (B9) and #110 (S21
control).

<a id="phase0"></a>
## Phase 0: is #30 still in the queue?

- **Question.** S9 left #30 with an "added to merge queue" event and no
  removal. Does GitHub still hold it as a queue entry, which could change how
  round 2's groups are built?
- **Observed.** [Lab] The GraphQL `repository.mergeQueue(branch: "main")` query
  ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42321642377)) returned `entries.totalCount: 0` on 2026-11-07, and
  Renovate's [#50](https://github.com/minulo-lab/merge-queue-lab/pull/50), [#51](https://github.com/minulo-lab/merge-queue-lab/pull/51) and [#52](https://github.com/minulo-lab/merge-queue-lab/pull/52), merged after round 1, had groups built on
  `main`'s tip, not behind #30. Decision: nothing to dequeue; #30 stays as S9
  evidence ([results/phase0-queue-ops.json](results/phase0-queue-ops.json)).
- Side observation: GraphQL reports `configuration.checkResponseTimeout: 600`
  for a ruleset whose `check_response_timeout_minutes` is 10. The schema
  describes the field as "the amount of time in minutes"; the value is in
  seconds.
- A caveat found later (S24b): for a few seconds before the queue merges a PR,
  the list can show 0 entries while the PR is not yet merged. A single empty
  listing does not prove that a PR left the queue; #30 has been in this state
  for over two weeks.

<a id="s12"></a>
## S12: Terraform and the queue ruleset

- **Question.** When the `integrations/github` provider changes a `merge_queue`
  parameter of `github_repository_ruleset`, does it update the ruleset in place,
  or destroy and recreate it (which strands queued PRs, S9)?
- **Setup.** [`terraform/main.tf`](../terraform/main.tf): only the existing
  `main-merge-queue` ruleset, provider pinned to 6.9.0, imported with
  `terraform import github_repository_ruleset.main_merge_queue merge-queue-lab:25550677`.
- **Prediction.** [Docs: provider docs] `merge_queue` first appears in the
  provider's `repository_ruleset` docs at v6.6.0 (absent at v6.5.0), so the
  README's "≥ 6.6.0" holds. The docs do not say which attributes force
  replacement.
- **Observed.** [Lab] `terraform plan`
  ([results/s12-terraform.md](results/s12-terraform.md)):
  - After import, the config matched the live ruleset: `No changes`.
  - Changing the check timeout, the name, the target (`branch` → `tag`) or even
    the repository all planned **update in-place** (`0 to add, 1 to change`).
  - Renaming the resource address in the code (a common refactor) planned
    **destroy and create**. With a `moved` block, the same refactor planned no
    changes.
  - v6.9.0 rejects `allowed_merge_methods` inside `pull_request`
    ("An argument named "allowed_merge_methods" is not expected here."), though
    the provider docs on its `main` branch list it.
- **Not run.** `terraform apply` while PRs are queued ([#71](https://github.com/minulo-lab/merge-queue-lab/pull/71) and [#72](https://github.com/minulo-lab/merge-queue-lab/pull/72) were
  prepared for it): the session's permission policy refused to apply
  infrastructure changes without the owner's explicit go-ahead. The ruleset
  id before the planned apply is 25550677.
- **[Inference]** For this provider version, a parameter change is an in-place
  `PUT`, which S9 suggests is harmless to queued PRs; the replacement risk comes
  from refactoring resource addresses (or `for_each` keys) without `moved`.
  Whether an in-place `PUT` while PRs are queued leaves them alone is not
  observed here; every `apply-config.yml` run in this round is an in-place `PUT`
  of the same ruleset, but none ran while a PR was queued.

<a id="s13"></a>
## S13: an organization ruleset plus the repository's queue

- **Skipped.** Creating an organization ruleset needs the organization API, which
  the session's GitHub access did not allow ("sessions are bound to their
  configured repositories"), and an organization-settings change needs the
  owner's approval. [Docs: available rules for rulesets] "This rule is not
  available for rulesets created at the organization level."

<a id="s14"></a>
## S14: two queues on one branch

- **Skipped.** The classic "Require merge queue" checkbox has no API field
  (round 1); it needs a click in **Settings → Branches → Add rule → Require merge
  queue**, which the owner did not do in this round. [Docs: changelog
  2024-02-27] "Multiple merge queues configured against a single branch will
  prevent merging."

<a id="s15"></a>
## S15: dequeue an entry in the middle

- **Question.** Queue 3 PRs and dequeue the second. Is the third's group
  rebuilt, and what does it cost?
- **Steps.** [#56](https://github.com/minulo-lab/merge-queue-lab/pull/56), [#57](https://github.com/minulo-lab/merge-queue-lab/pull/57), [#58](https://github.com/minulo-lab/merge-queue-lab/pull/58) enqueued at 01:17:06–09 UTC; `queue dequeue 57`
  (GraphQL `dequeuePullRequest`, as `github-actions[bot]`) at 01:17:42.
- **Prediction.** [Docs: managing a merge queue] Not described for a manual
  removal; the failing-CI example says the queue "recreates the temporary
  branch" of the PR behind.
- **Observed.** [Lab] The mutation returned #57's entry as it was: position 2,
  `AWAITING_CHECKS`. GitHub recorded the removal with reason `manual`, actor
  `github-actions`. 16 seconds later it built a new `pr-58` group on top of
  `pr-56`'s group commit. #56 merged at 01:19:43, #58 at 01:19:59.
  The orphaned `pr-57` run and the superseded `pr-58` run were **not
  cancelled**; both ran to success. 4 queue runs landed 2 PRs
  ([results/s15-dequeue.json](results/s15-dequeue.json)).
- A `GITHUB_TOKEN` bot can dequeue, and the rebuild it causes still gets CI
  (the new group's run has the original enqueuer as actor).

<a id="s16"></a>
## S16: jump to the front

- **Question.** What happens to groups already building, who may jump, and what
  does it cost?
- **Steps.** [#59](https://github.com/minulo-lab/merge-queue-lab/pull/59), [#60](https://github.com/minulo-lab/merge-queue-lab/pull/60), [#61](https://github.com/minulo-lab/merge-queue-lab/pull/61) enqueued at 01:20:32–35; [#62](https://github.com/minulo-lab/merge-queue-lab/pull/62) enqueued with
  `enqueuePullRequest(jump: true)` as `github-actions[bot]` at 01:21:05.
- **Prediction.** [Docs: managing a merge queue] "jumping to the top of a merge
  queue will cause a full rebuild of all in-progress pull requests".
- **Observed.** [Lab] The jump worked: the queue listing showed #62 at position
  1 (`jump: true`, enqueuer `github-actions`) and #59–#61 rebuilt behind it
  (#59's base became #62's group commit). Their rebuilt groups got CI, actor
  `minulo`, and passed by 01:23:19. **#62's own group never got a
  `merge_group` run**, so nothing merged: the whole queue waited behind it.
  GitHub removed #62 at 01:34:55, 13 min 50 s after it was enqueued, reason
  `checks_timed_out`, and rebuilt #59–#61 a third time. They merged at
  01:39:31 and 01:40:12, 19 minutes after they were enqueued. 9 queue runs for 3
  merges ([results/s16-jump.json](results/s16-jump.json)). The third build was
  also slowed by runner congestion from 31 PRs opened meanwhile.
- **[Inference]** The same mechanism as B3: a group enqueued with
  `GITHUB_TOKEN` gets no workflow runs. With a jump, that group sits at the
  front, so a bot that jumps the queue stalls everyone for the check timeout.
  A person or an App token should jump; this lab did not test a person's jump
  (GraphQL was not available to the driver).

<a id="s17"></a>
## S17: push a new commit to a queued PR

- **Question.** Is the PR removed, with which reason, and do groups behind it
  rebuild?
- **Prediction.** Undocumented (the merge-queue pages don't mention updating a
  queued PR's branch).
- **Observed.** [Lab] **The push is refused.** [#63](https://github.com/minulo-lab/merge-queue-lab/pull/63) and [#64](https://github.com/minulo-lab/merge-queue-lab/pull/64) were queued; a
  `git push` to #63's branch was rejected (`protected branch hook declined`), and
  both merged normally at 01:44:06. Repeated with [#102](https://github.com/minulo-lab/merge-queue-lab/pull/102) and [#103](https://github.com/minulo-lab/merge-queue-lab/pull/103) to capture the
  message ([results/s17b-push.md](results/s17b-push.md)):
  > GH006: Protected branch update failed for refs/heads/lab/s17b-lane-1.
  > A pull request for this branch has been added to a merge queue. Branches
  > that are queued for merging cannot be updated. To modify this branch,
  > dequeue the associated pull request.

  A commit through the contents API, as `github-actions[bot]`, on queued [#106](https://github.com/minulo-lab/merge-queue-lab/pull/106)
  got HTTP 409 with the same text ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42326746492)). No PR was removed;
  all of them merged.

<a id="s18"></a>
## S18: close a queued PR; delete a queued PR's head branch

- **Steps.** (a) [#65](https://github.com/minulo-lab/merge-queue-lab/pull/65), [#66](https://github.com/minulo-lab/merge-queue-lab/pull/66), [#67](https://github.com/minulo-lab/merge-queue-lab/pull/67) queued; #65 closed at 01:45:02. (b) [#105](https://github.com/minulo-lab/merge-queue-lab/pull/105),
  [#106](https://github.com/minulo-lab/merge-queue-lab/pull/106), [#107](https://github.com/minulo-lab/merge-queue-lab/pull/107) queued; #105's head branch deleted at 01:57:08 by
  `github-actions[bot]` (`queue-ops delete-head`, [run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42326722834)).
- **Observed.** [Lab]
  - (a) The queue removed #65 two seconds after it was closed, reason `manual`.
    #66's and #67's groups were rebuilt; the superseded `pr-67` run still ran to
    success. Both merged at 01:47:39.
  - (b) Deleting the branch **was allowed**, unlike pushing to it (S17): the
    PR was closed by `github-actions[bot]` and removed from the queue a second
    later, reason `manual`. #106 and #107 merged at 01:59:50.
  - The first attempt at (b), a `git push --delete` from the driver, was blocked
    by the driver's own network proxy (HTTP 403), not by GitHub.

<a id="s19"></a>
## S19: reviews change after enqueue

- **Setup.** `apply queue --approvals 1` ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42327047455)).
  `github-actions[bot]` approved [#111](https://github.com/minulo-lab/merge-queue-lab/pull/111) and [#112](https://github.com/minulo-lab/merge-queue-lab/pull/112) (`queue-ops approve`); both
  became `clean` and were enqueued at 02:03:35.
- **Steps.** (a) The bot requested changes on #111 at 02:03:56. (b) The repository
  owner dismissed #112's only approval at 02:04:07.
- **Prediction.** [Docs: bots.md, round 1] Approvals are checked before a PR
  can enter the queue; whether they are checked again inside is undocumented.
- **Observed.** [Lab] **Both merged** at 02:06:12. The queue does not re-check
  reviews once a PR is inside.

<a id="s20"></a>
## S20: draft PRs

- **Steps.** [#70](https://github.com/minulo-lab/merge-queue-lab/pull/70) opened as a draft. Enqueue with the async API, then
  `gh pr merge` and `gh pr merge --auto` (gh 2.103.3, as the bot).
- **Prediction.** [Docs: REST] "If the pull request cannot be merged (e.g.
  because it is closed, or still a draft) this result will be returned
  immediately with a `400` response status."
- **Observed.** [Lab]
  - async API: HTTP 400 at once, `"Pull request is in draft."`
  - `gh pr merge` and `gh pr merge --auto`: both
    `GraphQL: Pull request Pull request is a draft (enablePullRequestAutoMerge)`,
    exit 1 ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42322537722), [run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42322624650)). On a queue
    branch gh uses the auto-merge mutation even without `--auto`.
  - Control: marked ready for review, #70 entered the queue and merged at
    01:56:24.

<a id="s21"></a>
## S21: conversation resolution

- **Setup.** `apply queue --thread-resolution`; the rule read back
  `required_review_thread_resolution: true` ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42328333382)).
- **Steps.** [#114](https://github.com/minulo-lab/merge-queue-lab/pull/114) enqueued at 02:17:34; an unresolved review thread added at
  02:17:52.
- **Observed.** [Lab] #114 merged at 02:20:13 with the thread still unresolved.
  Control: on [#110](https://github.com/minulo-lab/merge-queue-lab/pull/110), a thread added *before* enqueueing made the async API
  answer `failed`: "Pull request could not be added to the merge queue: Pull
  request A conversation must be resolved before this pull request can be
  merged." So conversation resolution, like reviews (S19), is checked only at
  entry. (A first attempt on [#73](https://github.com/minulo-lab/merge-queue-lab/pull/73) ran with the rule off because of a lab.py bug,
  fixed in [#113](https://github.com/minulo-lab/merge-queue-lab/pull/113); it is not counted.)

<a id="s22"></a>
## S22: HEADGREEN vs ALLGREEN with a failing middle entry

- **Setup.** Three lanes; lane 2 carries a test that fails only in its *own*
  merge group (the head commit's subject contains "lane 2"), a stand-in for a
  flaky test. PRs were enqueued one at a time, waiting for each to be accepted.
- **Prediction.** [Docs: available rules] ALLGREEN: "each item in the merge
  group must pass all required checks"; HEADGREEN: "only the commit at the head
  of the merge group … must pass its required checks to merge."
- **Observed.** [Lab]

  | Run | PRs | Lane 2's group | What merged | Removed | Queue runs | Landing |
  | --- | --- | --- | --- | --- | --- | --- |
  | HEADGREEN | [#77](https://github.com/minulo-lab/merge-queue-lab/pull/77), [#78](https://github.com/minulo-lab/merge-queue-lab/pull/78), [#79](https://github.com/minulo-lab/merge-queue-lab/pull/79) | failed | **all three**, together at 02:29:54 | none | 3 | 2.6 min |
  | ALLGREEN | [#115](https://github.com/minulo-lab/merge-queue-lab/pull/115), [#116](https://github.com/minulo-lab/merge-queue-lab/pull/116), [#117](https://github.com/minulo-lab/merge-queue-lab/pull/117) | failed | #115 at 02:33:33, #117 at 02:35:54 | #116, `failed_checks` | 4 | 5.0 min |

  Under ALLGREEN, #117's first group had **passed**, but it was discarded and
  rebuilt on #115 after #116 was removed.
  ([results/s22b-headgreen.json](results/s22b-headgreen.json),
  [results/s22c-allgreen.json](results/s22c-allgreen.json))
- **HEADGREEN's cost showed up at once.** #78's failing test landed on `main`
  with it, and the next lane-2 PR in the lab ([#81](https://github.com/minulo-lab/merge-queue-lab/pull/81), S23) failed its group because
  of it. A cleanup PR, [#118](https://github.com/minulo-lab/merge-queue-lab/pull/118), removed the test.
- A first ALLGREEN run, [#74](https://github.com/minulo-lab/merge-queue-lab/pull/74)–[#76](https://github.com/minulo-lab/merge-queue-lab/pull/76), sent the three async requests one second
  apart; GitHub queued #76 before #75, so the failing lane was last and was
  simply removed. Async requests are not necessarily processed in the order
  sent ([results/s22a-allgreen.json](results/s22a-allgreen.json)).

<a id="s23"></a>
## S23: batching

- **Setup.** `--min-group 3 --max-group 5 --wait 3`
  ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42331819033)).
- **Prediction.** [Docs: managing a merge queue] "Merge limits do not combine
  `merge_group` builds. Merge limits only affect merges to the base branch";
  the wait time lets "smaller groups … merge if there are no more PRs queued".
- **Observed.** [Lab] ([results/s23-batching.json](results/s23-batching.json))
  - [#119](https://github.com/minulo-lab/merge-queue-lab/pull/119), [#120](https://github.com/minulo-lab/merge-queue-lab/pull/120), [#121](https://github.com/minulo-lab/merge-queue-lab/pull/121): each got its own group build, then all three merged
    at 03:02:03 in **one fast-forward**: three squash
    commits on `main`, one `push` run (for the tip).
  - [#122](https://github.com/minulo-lab/merge-queue-lab/pull/122) alone: its group passed at 03:04:13 and it merged at 03:06:46, 4.6
    minutes after enqueue. An earlier lone PR ([#83](https://github.com/minulo-lab/merge-queue-lab/pull/83)) took 6.4 minutes. The timer
    released the smaller group, but not exactly 3 minutes after the first PR
    was added.
  - The first attempt ([#80](https://github.com/minulo-lab/merge-queue-lab/pull/80)–[#83](https://github.com/minulo-lab/merge-queue-lab/pull/83)) was spoiled by S22b's test on `main`.

<a id="s24"></a>
## S24: build concurrency

- **Prediction.** [Docs: available rules] "if there are 5 pull requests added to
  the queue and the build concurrency setting is 3, merge queue will dispatch the
  `checks_requested` event for the first 3 … When it receives a result for one
  of those pull requests, merge queue will dispatch the event for the 4th";
  "If you set build concurrency to `0`, … Pull requests waiting for a merge
  queue build do not progress".
- **Observed.** [Lab]
  - (a) Concurrency 1, [#84](https://github.com/minulo-lab/merge-queue-lab/pull/84)–[#86](https://github.com/minulo-lab/merge-queue-lab/pull/86): strictly serial. Each group started only after
    the previous PR merged (03:08:06, 03:10:21, 03:12:39): 7.2 minutes for 3 PRs,
    3 queue runs ([results/s24a-build1.json](results/s24a-build1.json)).
  - (b) Concurrency 0, [#87](https://github.com/minulo-lab/merge-queue-lab/pull/87): for 3 minutes nothing was built: no group branch,
    no run; the queue listing showed it `QUEUED` with no base or head commit.
    After restoring 5 at 03:19:30, GitHub dispatched the group at 03:23:44
    (about 4 minutes later) and #87 merged at 03:26:02.
  - (c) 7 PRs with concurrency 5, [#88](https://github.com/minulo-lab/merge-queue-lab/pull/88)–[#94](https://github.com/minulo-lab/merge-queue-lab/pull/94): five groups at 03:27:17–21. The
    first results arrived at 03:29:04; #93's and #94's groups were dispatched at
    03:29:36, three seconds after the first five merged together (03:29:33,
    also the maximum group size). They merged at 03:31:53
    ([results/s24c-seven-over-five.json](results/s24c-seven-over-five.json)).
- **[Inference]** In (c) the freed slots were refilled after the merge rather
  than on the first result; one observation, so treat it as a hint.

<a id="s25"></a>
## S25: queue merge methods

- **Prediction.** [settings.md, round 1] A queue merge method the repository
  doesn't allow blocks merging. (Not from GitHub's docs.)
- **Observed.** [Lab]
  - **The mismatch is refused when the ruleset is saved.** Setting the queue to
    `MERGE` while the repository allows only squash: HTTP 422, "Invalid rule
    'merge_queue': Invalid merge method 'merge'. Not allowed for this
    repository." Same for `REBASE`.
  - `MERGE`, allowed by repository and ruleset ([#124](https://github.com/minulo-lab/merge-queue-lab/pull/124)): merged as a two-parent
    merge commit, signed by GitHub ("Merge pull request #124 from …").
  - `MERGE` queue, then the **repository** switched to squash-only ([#125](https://github.com/minulo-lab/merge-queue-lab/pull/125)): GitHub
    accepted the settings change, and #125 still merged as a merge commit. The
    queue uses its own method, whatever the repository settings say.
  - `REBASE` with the signed-commits ruleset on ([#97](https://github.com/minulo-lab/merge-queue-lab/pull/97), [#98](https://github.com/minulo-lab/merge-queue-lab/pull/98)): entered the queue
    and was removed 16 seconds later with no group CI, reason
    `branch_protection_failure`.
  - `REBASE` with the signed-commits ruleset briefly off ([#126](https://github.com/minulo-lab/merge-queue-lab/pull/126)): merged, but the
    commit on `main` is **unsigned** (`verified: false`, committer `minulo`). The
    ruleset was off from about 03:57 to 04:01:40 UTC.
  - [#95](https://github.com/minulo-lab/merge-queue-lab/pull/95) and [#96](https://github.com/minulo-lab/merge-queue-lab/pull/96) ran while a lab.py bug kept merge commits disallowed, so their
    queue was still SQUASH; they are not counted. The bug is fixed in [#123](https://github.com/minulo-lab/merge-queue-lab/pull/123).
- **[Inference]** Queue rebase merges replay the PR's commits without GitHub's
  signature, so "signatures on every branch" and a `REBASE` queue cannot be
  combined; use `SQUASH` or `MERGE`.

<a id="s26"></a>
## S26: a required check behind a `paths` filter

- **Setup.** `--require "Paths-filtered check"`, from
  [`paths-check.yml`](../.github/workflows/paths-check.yml): `pull_request` with
  `paths: ["src/**"]`, and `merge_group`.
- **Prediction.** [Docs: workflow syntax] Path filters apply to `push` and
  `pull_request`; `merge_group` only takes `branches` filters. What a required
  check does when its workflow is filtered out was not in the pages read.
- **Observed.** [Lab]
  - [#99](https://github.com/minulo-lab/merge-queue-lab/pull/99), which touches nothing under `src/`: the check never ran, so the PR
    could not enter the queue. The async API answered `failed`: "Pull request
    could not be added to the merge queue: Pull request Required status check
    "Paths-filtered check" is expected." It stays stuck.
  - [#100](https://github.com/minulo-lab/merge-queue-lab/pull/100), which touches `src/`: the check ran on the PR, ran again in the merge
    group (no `paths` filter there), and the PR merged at 04:05:18.
- Compare S6: a job skipped with `if:` reports a skipped result, which satisfies
  a required check; a workflow skipped by `paths` reports nothing.

<a id="s27"></a>
## S27: a required commit status

- **Setup.** `--require external-ci`; the lab pins every required check to the
  GitHub Actions app (`integration_id` 15368).
- **Steps.** `queue-ops status-head` posted `external-ci: success` (as
  `github-actions[bot]`) on [#101](https://github.com/minulo-lab/merge-queue-lab/pull/101)'s head commit; the PR became `clean` and was
  enqueued at 04:06:46. After 2.5 minutes, `status-group` posted the same status
  on the head commit of the PR's merge group.
- **Observed.** [Lab] With the status only on the PR's head, the group's CI
  passed and the PR sat in the queue without merging. 21 seconds after the
  status was posted on the merge group's head commit, it merged (04:09:59). A
  status posted with `GITHUB_TOKEN` satisfied a requirement pinned to the
  GitHub Actions app.
- So an external CI that reports through the commit statuses API has to report
  on `gh-readonly-queue/*` commits too, as the docs say for third-party CI.

<a id="s28"></a>
## S28: workflows that react to queue events

- **Prediction.** [Docs: events that trigger workflows] `enqueued` and
  `dequeued` are `pull_request` activity types. The REST description's
  `dequeued` webhook has a `reason`: `UNKNOWN_REMOVAL_REASON`, `MANUAL`, `MERGE`,
  `MERGE_CONFLICT`, `CI_FAILURE`, `CI_TIMEOUT`, `ALREADY_MERGED`, `QUEUE_CLEARED`,
  `ROLL_BACK`, `BRANCH_PROTECTIONS`, `GIT_TREE_INVALID`, `INVALID_MERGE_COMMIT`.
- **Setup.** [`queue-events.yml`](../.github/workflows/queue-events.yml) writes
  action, reason and sender to its job summary.
- **Observed.** [Lab] 132 runs during round 2
  ([results/s28-queue-events.md](results/s28-queue-events.md)).
  `github.event.reason` matched GraphQL's reason every time:

  | GraphQL reason | `dequeued` reason | Example |
  | --- | --- | --- |
  | `merged` | `MERGE` | #54 |
  | `failed_checks` | `CI_FAILURE` | #75, #81, #116 |
  | `checks_timed_out` | `CI_TIMEOUT` | #62 |
  | `branch_protection_failure` | `BRANCH_PROTECTIONS` | #97, #98 |
  | `manual` | `MANUAL` | #65 (closed), #105 (branch deleted) |
  | `merge_conflict` | no run | #69 |

  Missing runs: the bot's dequeue of #57 and the bot's enqueue of #62 (events
  caused by `GITHUB_TOKEN` start no runs), and everything for #69, the PR with
  a merge conflict ([Docs] "Workflows will not run on `pull_request` activity if
  the pull request has a merge conflict"). `sender` was the enqueuing person for
  `MERGE`, and `github-merge-queue[bot]` for the other reasons.

<a id="s29"></a>
## S29: are superseded group runs cancelled?

- **Observed.** [Lab] No. In S15, S18 and S22c a rebuilt group's predecessor kept
  running to completion. `ci.yml`'s concurrency group is
  `ci-${{ github.ref }}` and cancels only for `pull_request`; each merge group has
  its own `gh-readonly-queue/main/pr-<n>-<sha>` ref, so no two group runs share
  a concurrency group.
- **[Inference]** Grouping by PR number instead
  (`github.event.merge_group.head_ref` without its SHA suffix) would let a
  rebuild cancel the run it replaces, saving the minutes S15 and S16 wasted.

<a id="s30"></a>
## S30: the async merge API, with its result polled

- **Why.** Round 1 concluded that refused async requests were "silently
  dropped" (S7, S11, B3), but never called the documented result endpoint.
- **Prediction.** [Docs: REST] `GET /repos/{owner}/{repo}/pulls/{n}/merge-async/{uuid}`
  returns `merged`, `enqueued` or `failed`; "`failed`: The request failed. The
  response includes a message describing the failure." Results are kept for 24
  hours.
- **Observed.** [Lab] ([results/s30-async.json](results/s30-async.json))

  | PR | Request | First answer | Polled result |
  | --- | --- | --- | --- |
  | [#69](https://github.com/minulo-lab/merge-queue-lab/pull/69) | `merge_queue` while checks were running | `pending` | `failed`: "Pull request could not be added to the merge queue: Pull request Required status check "Required checks" is expected." |
  | [#68](https://github.com/minulo-lab/merge-queue-lab/pull/68) | `direct_merge`, no `merge_method` | `pending` | `failed`: "Merge commits are not allowed on this repository." (same with `bypass_rules`) |
  | [#68](https://github.com/minulo-lab/merge-queue-lab/pull/68) | `direct_merge`, `merge_method: squash` | `pending` | `failed`: "Repository rule violations found … Changes must be made through the merge queue" (same with `bypass_rules`) |
  | [#68](https://github.com/minulo-lab/merge-queue-lab/pull/68) | `merge_queue` (control) | `pending` | `enqueued`; merged 2.6 min later |
  | [#69](https://github.com/minulo-lab/merge-queue-lab/pull/69) | `merge_queue` after a conflicting PR merged | `pending` | `enqueued` (GitHub had not yet computed the conflict); removed 16 s later, `merge_conflict` |
  | [#70](https://github.com/minulo-lab/merge-queue-lab/pull/70) | `merge_queue` on a draft | HTTP 400 | — |

- **Corrections to round 1.**
  - The async API does not drop requests silently: it reports the failure and
    its reason at the result endpoint. S11's early enqueue and S7's refused
    direct merges would have shown `failed` had round 1 polled.
  - S7's async `direct_merge` probes sent no `merge_method`, so they were refused
    for the repository's merge methods before the queue rule was even reached.
    With `squash`, the refusal is the expected "Changes must be made through the
    merge queue", with or without `bypass_rules`. S7's conclusion stands; its
    evidence for the async path did not show it.
  - S5's [Inference] that unsigned commits on a PR branch "would not trip the
    rule" is contradicted by GitHub's docs: "unsigned commits on the head branch
    can block a squash merge, even though GitHub would sign the final squash
    commit." Round 2 didn't test it.

<a id="b6"></a>
## B6: a GitHub App installation token enqueues

- **Skipped.** Creating a GitHub App needs the owner. Renovate (B1) remains the
  only App-token evidence.

<a id="b7"></a>
## B7: Dependabot

- **Skipped.** The scenario needs a workflow that enables auto-merge with an App
  token or PAT (which the owner would have to create), and [Inference] Renovate
  already keeps this repository's dependencies current, so version updates
  would likely open no PRs. [Docs: automating Dependabot with GitHub Actions, round 1] "the
  built-in `GITHUB_TOKEN` cannot add pull requests to the queue."

<a id="b8"></a>
## B8: Renovate `automergeType: branch` behind a queue

- **Skipped.** Renovate reads its configuration from the default branch, so
  testing it means changing `renovate.json` on `main`, adding `renovate/**` to
  CI, and waiting for Renovate's own schedule and a real update.
- **Prediction.** [Docs: Renovate automerge, read 2026-11-07] "Branch automerge
  (`automergeType=branch`) only works if the base branch has a merge queue when
  Renovate is on the merge queue's bypass list … Renovate logs a warning and
  creates a PR instead if the merge queue rejects the push."

<a id="b9"></a>
## B9: `gh pr merge` without `--auto`, and with `--admin`

- **Prediction.** [gh source, `pkg/cmd/pr/merge/merge.go`] On a queue branch gh
  adds the PR to the queue (through `enablePullRequestAutoMerge`) unless
  `--admin` is passed, in which case it merges directly.
- **Observed.** [Lab] As `github-actions[bot]` (gh 2.103.3), because the driver
  could not use GraphQL:
  - `--admin --squash` on green [#108](https://github.com/minulo-lab/merge-queue-lab/pull/108): gh skipped the queue and called
    `mergePullRequest`, which GitHub refused: "Repository rule violations
    found … Changes must be made through the merge queue" (exit 1,
    [run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42326986197)).
  - Without flags: S20 shows gh takes the `enablePullRequestAutoMerge` path even
    without `--auto`. On a green PR, as the bot, that is B3's path 3 (enqueued,
    no group CI, removed at the timeout), so it was not repeated. A person's
    `gh pr merge` was not tested.

<a id="b10"></a>
## B10: a fork PR in the queue

- **Skipped.** It needs a second account to open the fork PR.
