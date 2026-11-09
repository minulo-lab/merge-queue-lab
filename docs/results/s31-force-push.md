# S31: force-push of a rebased commit to a queued PR (#130)

Pushed at 2026-11-09T22:00:59Z with `git push --force-with-lease`, while #130 was in the merge queue. Literal output:

```
remote: error: GH006: Protected branch update failed for refs/heads/lab/s31-lane-3.        
remote: 
remote: - A pull request for this branch has been added to a merge queue. Branches that        
remote:   are queued for merging cannot be updated. To modify this branch, dequeue the        
remote:   associated pull request.        
To https://github.com/minulo-lab/merge-queue-lab
 ! [remote rejected] lab/s31-lane-3 -> lab/s31-lane-3 (protected branch hook declined)
error: failed to push some refs to 'https://github.com/minulo-lab/merge-queue-lab'
```
