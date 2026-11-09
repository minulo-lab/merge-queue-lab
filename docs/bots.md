# Bots and the merge queue

A bot is just another actor to GitHub. What it can do depends on **which token
it acts with**, and that one fact decides four things:

- whether its pull requests trigger CI
- whether it can approve
- whether it can merge or enqueue
- whether its commits are signed

## The four bot identities

| Identity | Example | Its events trigger workflows? | Can add a PR to the queue? | Commits signed? |
| --- | --- | --- | --- | --- |
| GitHub App installation token | Renovate (`renovate[bot]`) | Yes | Yes, through auto-merge or the API | Yes, when it commits through the API |
| `GITHUB_TOKEN` of a workflow | `github-actions[bot]` | Mostly no. PR open, sync and reopen start **approval-required** runs (since 2026-06-11); a group it enqueues gets no `merge_group` runs, and its enqueue/dequeue start no `pull_request` runs ([S28](scenarios.md#s28)) | **Not usefully.** It can enqueue an already-green PR with `gh pr merge --auto`, but the group gets no CI and times out ([B3](scenarios.md#b3)); a jump stalls the whole queue ([S16](scenarios.md#s16)). It *can* dequeue, and the rebuilt groups still get CI ([S15](scenarios.md#s15)) | Yes through the API; no through `git push` without a key |
| Dependabot | `dependabot[bot]` | Yes, but treated like a fork: read-only token, no Actions secrets | Only through a workflow that uses a PAT or App token | Yes |
| Personal access token or App token in a workflow | a custom bot | Yes | Yes | Through the API |

Sources:

- [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
  and the [2026-06-11 changelog](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/)
- [Automating Dependabot with GitHub Actions](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/automating-dependabot-with-github-actions),
  which says "the built-in `GITHUB_TOKEN` cannot add pull requests to the queue"
- [Dependabot on Actions](https://docs.github.com/en/code-security/reference/supply-chain-security/troubleshoot-dependabot/dependabot-on-actions)
- [Renovate: automerge and GitHub merge queue](https://docs.renovatebot.com/key-concepts/automerge/#github-merge-queue)

## Patterns that keep working with a queue

- **What the lab saw with Renovate ([B1](scenarios.md#b1)).** Auto-merge put
  each PR in the queue as soon as its checks passed, and every PR merged through
  the queue with `renovate[bot]` as the merger. Two PRs that edited lines next to
  another queued PR's lines were removed when that PR merged; Renovate rebased them
  within a minute and they merged on the second pass.
- **Platform auto-merge (Renovate's default).** "With `platformAutomerge`
  enabled (which is the default), GitHub's auto-merge takes care of adding the PR
  to the merge queue." This needs "Allow auto-merge" in the repository settings.
  [Renovate docs]
- **Bot approval by workflow.** If every PR needs an approval, a workflow can
  approve trusted bot PRs as `github-actions[bot]` (see
  [`bot-approve.yml`](../.github/workflows/bot-approve.yml)). Approvals are
  checked *before* a PR can enter the queue, so nothing changes inside the queue.
  The organization and repository must allow GitHub Actions to approve PRs.
- **Fewer rebases.** With a queue, Renovate's `rebaseWhen=auto` behaves like
  `conflicted`, "because the merge queue already tests PRs against the head of
  the base branch". [Renovate docs, `rebaseWhen`]

## Patterns that break with a queue

| Pattern | What happens | Fix | Scenario |
| --- | --- | --- | --- |
| A workflow enables auto-merge with `GITHUB_TOKEN` | Auto-merge turns on but never enqueues; on an already-green PR gh enqueues it, then the group gets no `merge_group` runs and is removed "due to no response for status checks" | Use a GitHub App token or PAT for that step, or let a person enqueue | [B3](scenarios.md#b3) |
| `gh pr merge --auto --squash --delete-branch` | gh refuses `--delete-branch` when the base requires a queue | Drop `--delete-branch`; let "delete head branches" do it | [B4](scenarios.md#b4) |
| Bot merges through the REST merge endpoint | The endpoint "does not support … merging with a merge queue" | Use auto-merge, or the async merge API with `merge_action: merge_queue` | [S7](scenarios.md#s7) |
| Renovate `automergeType: branch` | Pushing straight to the base branch is impossible behind a queue unless Renovate is a bypass actor; Renovate "logs a warning and creates a PR instead" | Use `automergeType: pr` (the default) | [Renovate docs], [B8](scenarios.md#b8) (not run) |
| A bot jumps the queue with `GITHUB_TOKEN` (`enqueuePullRequest(jump: true)`) | The jumped group gets no CI and sits at the front; every PR behind waits for the check timeout | Jump with an App token or PAT, or let a person do it | [S16](scenarios.md#s16) |
| A bot pushes to, force-pushes (rebases) or "Update branch"es a PR that is already queued | Refused: "Branches that are queued for merging cannot be updated" (GH006 for `git`, HTTP 409 for the contents API, HTTP 422 for update-branch). The PR stays queued and merges with no removal | Let the bot skip queued PRs, or dequeue first, push, enqueue again (the dequeue is a removal) | [S17](scenarios.md#s17), [S31](scenarios.md#s31) |
| `gh pr merge --admin` on a queue branch | gh skips the queue and calls `mergePullRequest`; GitHub refuses unless the actor may bypass the ruleset | Drop `--admin`, or add the actor to the bypass list | [B9](scenarios.md#b9) |
| A bot pushes commits with `git push` and no signing key, on a repo that requires signatures everywhere | The push is rejected | Commit through the API (GitHub signs), or give the bot a signing key | [B5](scenarios.md#b5) |
| A required check that skips bots with `if: github.event.pull_request.user.type != 'Bot'` | In a merge group `null != 'Bot'` is true, so the check runs, and for PR-shaped checks it fails | `if: github.event_name == 'pull_request' && …` | [S6](scenarios.md#s6) |

## Approving runs of `GITHUB_TOKEN` pull requests

Since 2026-06-11, a PR opened or updated with `GITHUB_TOKEN` starts its
`pull_request` runs in an approval-required state ([B2](scenarios.md#b2)).
Someone with write access clicks **Approve workflows to run** on the PR, or calls
`POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve` (the endpoint
documented for fork PRs also worked here; it needs `actions: write`). The
approved run's `triggering_actor` is the approver.

## Measuring a bot's queue churn

`scripts/lab.py churn --since <date> --author '<bot>[bot]' --repo owner/name`
counts, per merged PR, how many times it left the queue without merging
([S32](scenarios.md#s32)). In this lab Renovate's rate was 0.22 (two
`merge_conflict` removals in B1) and 0 since.

