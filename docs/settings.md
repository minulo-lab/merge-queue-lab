# Settings reference

The protection models used in this lab, as files and as configuration-as-code.

## Files in `config/`

| File | Applied with | What it sets |
| --- | --- | --- |
| `repo-settings.json` | `scripts/lab.py apply settings` (PATCH `/repos/{owner}/{repo}`) | Squash merges only, auto-merge allowed, "update branch" suggested, head branches deleted after merge |
| `classic-protection.json` | `scripts/lab.py apply classic` (PUT `…/branches/main/protection`, then POST `…/protection/required_signatures`) | Strict required checks (`Required checks`), `enforce_admins: true`, PR reviews (count set by `--approvals`), no force pushes or deletion, signatures on `main` |
| `ruleset-main-merge-queue.json` | `scripts/lab.py apply queue` (POST or PUT `/repos/{owner}/{repo}/rulesets`) | On the default branch: no deletion, no force push, PR required (squash only), required checks with strict policy, merge queue |
| `ruleset-signed-commits.json` | `scripts/lab.py apply signed-commits` | `required_signatures` on `~ALL` branches except `refs/heads/gh-pages`; empty bypass list |

You can also import any ruleset file in the web UI: **Settings → Rules →
Rulesets → New ruleset → Import a ruleset**.

## The merge-queue rule, field by field

Ranges are from GitHub's REST schema. Defaults are not documented by GitHub; the
values below are this lab's choices.

| Field | This lab | Range | Meaning |
| --- | --- | --- | --- |
| `merge_method` | `SQUASH` | `MERGE`, `SQUASH`, `REBASE` | Must agree with the repository's allowed merge methods, or merging is blocked |
| `grouping_strategy` | `ALLGREEN` | `ALLGREEN`, `HEADGREEN` | Every entry must pass, or only the group's head |
| `max_entries_to_build` | 5 | 0–100 | Groups building at once (0 pauses the queue) |
| `min_entries_to_merge` / `max_entries_to_merge` | 1 / 5 | 0–100 | PRs merged together |
| `min_entries_to_merge_wait_minutes` | 0 | 0–360 | Wait for the minimum group size |
| `check_response_timeout_minutes` | 10 | 1–360 | Silence longer than this counts as failure |

## Configuration as code

- **Classic branch protection has no API field for "Require merge queue".** The
  checkbox exists only in the UI.
  [REST schema](https://docs.github.com/en/rest/branches/branch-protection),
  [GraphQL](https://docs.github.com/en/graphql/reference/branches)
- **Terraform (integrations/github).** Only `github_repository_ruleset` has a
  `merge_queue` block, added in
  [v6.6.0](https://github.com/integrations/terraform-provider-github/releases/tag/v6.6.0).
  `github_branch_protection` and `github_organization_ruleset` have none. The
  provider's `merge_method` default is `MERGE`, so set it to `SQUASH` if the
  repository only allows squash.
- **Organization rulesets cannot hold the merge-queue rule.** "This rule is not
  available for rulesets created at the organization level."
  [GHEC docs](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- **Don't configure two queues for one branch** (one classic, one ruleset):
  "Multiple merge queues configured against a single branch will prevent
  merging."
  [Changelog 2024-02-27](https://github.blog/changelog/2024-02-27-repository-rules-configure-merge-queue-rule-public-beta)
- **Wildcard patterns aren't supported** for a queued branch.
  [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

## Running the lab from GitHub Actions

Five workflows let you drive the lab without an admin token on your own machine.
All are `workflow_dispatch` only, so only people with write access can run them.

| Workflow | Token it uses | What it does |
| --- | --- | --- |
| `apply-config.yml` | `LAB_ADMIN_TOKEN` secret | Runs `scripts/lab.py apply <model>`. Changing rulesets and branch protection needs **Administration: write**. Create a fine-grained token for this repository only, with Administration read/write and a short expiry, and store it as the `LAB_ADMIN_TOKEN` repository secret |
| `prepare-branches.yml` | `GITHUB_TOKEN` | Creates a scenario's branches and commits through the contents API. GitHub signs those commits, so this works while the signed-commits ruleset is on. Then open the PRs yourself with `scripts/lab.py open <kind> --tag <tag> --phase prs`, so they are not bot-authored |
| `bot-pr.yml` | `GITHUB_TOKEN` | Opens a PR as `github-actions[bot]` (scenarios B2–B5) |
| `bot-enqueue.yml` | `GITHUB_TOKEN` | Asks GitHub to merge an existing PR as `github-actions[bot]` (scenario B3) |
| `inspect-queue.yml` | `GITHUB_TOKEN` | Lists PRs' merge-queue events with GitHub's removal reason (GraphQL), published as a check run named "Merge queue events" |

Example, with the GitHub CLI:

```bash
gh workflow run apply-config.yml -f model=queue -f approvals=0 -f timeout=10
gh workflow run prepare-branches.yml -f kind=lanes -f n=4 -f tag=s2
scripts/lab.py open lanes --n 4 --tag s2 --phase prs
```

Changes to the lab's own files (workflows, `scripts/`, docs) were pushed with
`git` and therefore unsigned. They were landed in short maintenance windows:
`apply-config.yml -f model=signed-commits-off`, push, open the PR, let the queue
merge it (the squash commit on `main` is created and signed by GitHub), then
`-f model=signed-commits`. PRs #11, #15, #16, #46 and the results PR were
landed this way and say so in their description. PR #1 was merged directly, in
the same kind of window, before the queue existed. The repository's first two commits were pushed before any rule
existed, so they are the only unsigned commits on `main`.

## The `restricted` model (scenario S10)

`scripts/lab.py apply restricted --push-apps renovate [--push-users a,b] [--enforce-admins]`
adds classic branch protection whose only job is **Restrict who can push to
matching branches**, on top of the merge-queue ruleset (run `apply queue`
first). Checks and reviews stay in the ruleset. It answers one question: do push
allowances get in the way of the queue's merge?
