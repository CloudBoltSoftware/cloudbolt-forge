"""
Sample hook to test hook failures.

This hook always returns ("FAILURE", "", "").
"""


def run(job, logger=None):
    return (
        "FAILURE",
        "This hook intentionally failed. This is the output.",
        "This hook fails every time. This is the error detail.",
    )
