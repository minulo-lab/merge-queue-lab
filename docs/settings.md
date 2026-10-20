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
