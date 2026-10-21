# Merge-queue events and removal reasons

Collected on 2026-10-21 with `inspect-queue.yml` (GraphQL `AddedToMergeQueueEvent` and `RemovedFromMergeQueueEvent`). A PR that never entered the queue has no rows: #13 and #33 (async requests that were dropped) do not appear. #30 shows an add with no removal: it was stranded in S9.

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


| #48 | AddedToMergeQueueEvent | 2026-10-21T16:13:10Z | minulo |  |
| #48 | RemovedFromMergeQueueEvent | 2026-10-21T16:15:49Z | github-merge-queue | branch_protection_failure |
| #47 | AddedToMergeQueueEvent | 2026-10-21T16:06:39Z | minulo |  |
| #47 | RemovedFromMergeQueueEvent | 2026-10-21T16:09:10Z | github-merge-queue | branch_protection_failure |

