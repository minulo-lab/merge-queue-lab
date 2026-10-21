"""A stand-in for a slow integration suite.

Real integration suites (deploying services, spinning up clusters) take many
minutes. That duration is what makes "update branch, wait, merge, repeat" painful
and what a merge queue parallelises. The sleep length comes from the environment
so the workflow, not the test, decides how slow "integration" is.
"""

import os
import time

from mqlab.pricing import discounted_price


def test_slow_integration_suite() -> None:
    """
    arrange: a simulated environment that takes MQLAB_INTEGRATION_SECONDS to come up
    act: wait for it, then exercise the public API end to end
    assert: the end-to-end result is correct
    """
    time.sleep(int(os.environ.get("MQLAB_INTEGRATION_SECONDS", "60")))
    assert discounted_price(200, 50) == 100
