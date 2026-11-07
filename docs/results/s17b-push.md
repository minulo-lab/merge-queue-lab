# S17b: git push to the head branch of a queued PR (#102)

Pushed at 2026-11-07T01:48:30Z, while #102 was in the merge queue. Literal output:

```
remote: error: GH006: Protected branch update failed for refs/heads/lab/s17b-lane-1.        
remote: 
remote: - A pull request for this branch has been added to a merge queue. Branches that        
remote:   are queued for merging cannot be updated. To modify this branch, dequeue the        
remote:   associated pull request.        
To https://github.com/minulo-lab/merge-queue-lab
 ! [remote rejected] lab/s17b-lane-1 -> lab/s17b-lane-1 (protected branch hook declined)
error: failed to push some refs to 'https://github.com/minulo-lab/merge-queue-lab'
```
