"""Scenario s22b: lane 2 fails, but only in a merge group."""

import os


def test_lane_2_fails_in_merge_groups() -> None:
    """
    arrange: the workflow event name
    act: nothing
    assert: fail when running for a merge group, pass otherwise
    """
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    assert event != "merge_group", "s22b lane 2 fails in merge groups on purpose"
