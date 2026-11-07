# Merge-queue events and removal reasons

Collected on 2026-10-21 with `inspect-queue.yml`, which reads GraphQL
`AddedToMergeQueueEvent` and `RemovedFromMergeQueueEvent` for a chosen list of
PRs. The list covers every PR that left the queue without merging, plus the
stranded S9 PRs. PRs that merged on their first attempt are not listed, and PRs
that never entered the queue (#13, #33: dropped async requests) have no events.
#30 has an add and no removal: it was stranded in S9.

| PR | Event | At (UTC) | Actor | Reason |
| --- | --- | --- | --- | --- |
| #6 | AddedToMergeQueueEvent | 2026-10-21T12:07:11Z | renovate |  |
| #6 | RemovedFromMergeQueueEvent | 2026-10-21T12:09:11Z | github-merge-queue | merge_conflict |
| #6 | AddedToMergeQueueEvent | 2026-10-21T12:11:50Z | renovate |  |
| #6 | RemovedFromMergeQueueEvent | 2026-10-21T12:14:30Z | github-merge-queue | merged |
| #7 | AddedToMergeQueueEvent | 2026-10-21T12:09:57Z | renovate |  |
| #7 | RemovedFromMergeQueueEvent | 2026-10-21T12:12:04Z | github-merge-queue | merge_conflict |
| #7 | AddedToMergeQueueEvent | 2026-10-21T12:15:21Z | renovate |  |
| #7 | RemovedFromMergeQueueEvent | 2026-10-21T12:18:05Z | github-merge-queue | merged |
| #17 | AddedToMergeQueueEvent | 2026-10-21T13:00:28Z | github-actions |  |
| #17 | RemovedFromMergeQueueEvent | 2026-10-21T13:11:15Z | github-merge-queue | checks_timed_out |
| #23 | AddedToMergeQueueEvent | 2026-10-21T13:21:07Z | minulo |  |
| #23 | RemovedFromMergeQueueEvent | 2026-10-21T13:23:42Z | github-merge-queue | failed_checks |
| #30 | AddedToMergeQueueEvent | 2026-10-21T13:44:05Z | minulo |  |
| #31 | AddedToMergeQueueEvent | 2026-10-21T13:44:07Z | minulo |  |
| #31 | AddedToMergeQueueEvent | 2026-10-21T14:09:04Z | minulo |  |
| #31 | RemovedFromMergeQueueEvent | 2026-10-21T14:11:31Z | github-merge-queue | merged |
| #34 | AddedToMergeQueueEvent | 2026-10-21T14:36:10Z | minulo |  |
| #34 | RemovedFromMergeQueueEvent | 2026-10-21T14:36:59Z | github-merge-queue | failed_checks |
| #36 | AddedToMergeQueueEvent | 2026-10-21T14:46:58Z | minulo |  |
| #36 | RemovedFromMergeQueueEvent | 2026-10-21T14:52:29Z | github-merge-queue | checks_timed_out |
| #37 | AddedToMergeQueueEvent | 2026-10-21T14:56:33Z | minulo |  |
| #37 | RemovedFromMergeQueueEvent | 2026-10-21T14:59:15Z | github-merge-queue | branch_protection_failure |
| #38 | AddedToMergeQueueEvent | 2026-10-21T15:05:48Z | minulo |  |
| #38 | RemovedFromMergeQueueEvent | 2026-10-21T15:09:28Z | github-merge-queue | branch_protection_failure |
| #47 | AddedToMergeQueueEvent | 2026-10-21T16:06:39Z | minulo |  |
| #47 | RemovedFromMergeQueueEvent | 2026-10-21T16:09:10Z | github-merge-queue | branch_protection_failure |
| #48 | AddedToMergeQueueEvent | 2026-10-21T16:13:10Z | minulo |  |
| #48 | RemovedFromMergeQueueEvent | 2026-10-21T16:15:49Z | github-merge-queue | branch_protection_failure |

## Round 2 (2026-11-07)

Collected with `inspect-queue.yml` ([run](https://github.com/minulo-lab/merge-queue-lab/actions/runs/42337300166)) for every round 2 PR that left the queue without merging, plus merged controls (#54, #70, #87, #101, #106, #111, #112, #114, #125, #126). The REST timeline and the `queue-events.yml` log ([s28-queue-events.md](s28-queue-events.md)) agree with these reasons.

| PR | Event | At (UTC) | Actor | Reason |
| --- | --- | --- | --- | --- |
| #54 | AddedToMergeQueueEvent | 2026-11-07T00:57:54Z | minulo |  |
| #54 | RemovedFromMergeQueueEvent | 2026-11-07T01:00:33Z | github-merge-queue | merged |
| #57 | AddedToMergeQueueEvent | 2026-11-07T01:17:07Z | minulo |  |
| #57 | RemovedFromMergeQueueEvent | 2026-11-07T01:17:42Z | github-actions | manual |
| #62 | AddedToMergeQueueEvent | 2026-11-07T01:21:05Z | github-actions |  |
| #62 | RemovedFromMergeQueueEvent | 2026-11-07T01:34:55Z | github-merge-queue | checks_timed_out |
| #65 | AddedToMergeQueueEvent | 2026-11-07T01:44:40Z | minulo |  |
| #65 | RemovedFromMergeQueueEvent | 2026-11-07T01:45:04Z | github-merge-queue | manual |
| #69 | AddedToMergeQueueEvent | 2026-11-07T01:16:29Z | minulo |  |
| #69 | RemovedFromMergeQueueEvent | 2026-11-07T01:16:45Z | github-merge-queue | merge_conflict |
| #70 | AddedToMergeQueueEvent | 2026-11-07T01:54:06Z | minulo |  |
| #70 | RemovedFromMergeQueueEvent | 2026-11-07T01:56:24Z | github-merge-queue | merged |
| #75 | AddedToMergeQueueEvent | 2026-11-07T02:23:11Z | minulo |  |
| #75 | RemovedFromMergeQueueEvent | 2026-11-07T02:25:40Z | github-merge-queue | failed_checks |
| #81 | AddedToMergeQueueEvent | 2026-11-07T02:36:55Z | minulo |  |
| #81 | RemovedFromMergeQueueEvent | 2026-11-07T02:42:27Z | github-merge-queue | failed_checks |
| #87 | AddedToMergeQueueEvent | 2026-11-07T03:16:09Z | minulo |  |
| #87 | RemovedFromMergeQueueEvent | 2026-11-07T03:26:02Z | github-merge-queue | merged |
| #97 | AddedToMergeQueueEvent | 2026-11-07T03:40:16Z | minulo |  |
| #97 | RemovedFromMergeQueueEvent | 2026-11-07T03:40:32Z | github-merge-queue | branch_protection_failure |
| #98 | AddedToMergeQueueEvent | 2026-11-07T03:41:16Z | minulo |  |
| #98 | RemovedFromMergeQueueEvent | 2026-11-07T03:41:32Z | github-merge-queue | branch_protection_failure |
| #101 | AddedToMergeQueueEvent | 2026-11-07T04:06:42Z | minulo |  |
| #101 | RemovedFromMergeQueueEvent | 2026-11-07T04:09:59Z | github-merge-queue | merged |
| #105 | AddedToMergeQueueEvent | 2026-11-07T01:56:42Z | minulo |  |
| #105 | RemovedFromMergeQueueEvent | 2026-11-07T01:57:12Z | github-merge-queue | manual |
| #106 | AddedToMergeQueueEvent | 2026-11-07T01:56:44Z | minulo |  |
| #106 | RemovedFromMergeQueueEvent | 2026-11-07T01:59:49Z | github-merge-queue | merged |
| #111 | AddedToMergeQueueEvent | 2026-11-07T02:03:36Z | minulo |  |
| #111 | RemovedFromMergeQueueEvent | 2026-11-07T02:06:12Z | github-merge-queue | merged |
| #112 | AddedToMergeQueueEvent | 2026-11-07T02:03:37Z | minulo |  |
| #112 | RemovedFromMergeQueueEvent | 2026-11-07T02:06:12Z | github-merge-queue | merged |
| #114 | AddedToMergeQueueEvent | 2026-11-07T02:17:36Z | minulo |  |
| #114 | RemovedFromMergeQueueEvent | 2026-11-07T02:20:13Z | github-merge-queue | merged |
| #116 | AddedToMergeQueueEvent | 2026-11-07T02:31:00Z | minulo |  |
| #116 | RemovedFromMergeQueueEvent | 2026-11-07T02:33:33Z | github-merge-queue | failed_checks |
| #125 | AddedToMergeQueueEvent | 2026-11-07T03:54:01Z | minulo |  |
| #125 | RemovedFromMergeQueueEvent | 2026-11-07T03:56:29Z | github-merge-queue | merged |
| #126 | AddedToMergeQueueEvent | 2026-11-07T03:57:45Z | minulo |  |
| #126 | RemovedFromMergeQueueEvent | 2026-11-07T04:00:24Z | github-merge-queue | merged |

