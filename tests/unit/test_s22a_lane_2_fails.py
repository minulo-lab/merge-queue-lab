"""Scenario s22a: lane 2 fails, but only in its own merge group (a stand-in for a flaky test)."""

import os
import subprocess


def test_lane_2_fails_in_its_own_merge_group() -> None:
    """
    arrange: the event name and the subject of the commit under test
    act: nothing
    assert: fail only when a merge group's head commit is lane 2's squash commit
    """
    if os.environ.get("GITHUB_EVENT_NAME") != "merge_group":
        return
    subject = subprocess.run(
        ["git", "log", "-1", "--format=%s"], capture_output=True, text=True, check=True
    ).stdout
    assert "lane 2" not in subject, f"s22a lane 2 fails in its own merge group: {subject!r}"
