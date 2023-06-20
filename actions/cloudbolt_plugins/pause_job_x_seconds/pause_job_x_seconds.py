import time
from common.methods import set_progress

SECONDS_TO_WAIT = {{SECONDS_TO_WAIT}}


def run(job, **kwargs):
    """
    This plugin can be used to pause the Job Engine and is useful within blueprints
    and other places where a pause in execution is required. A parameter specifying
    how many seconds to pause is passed to this script.
    """

    job.set_progress(
        "Pausing job for {} seconds".format(SECONDS_TO_WAIT),
        tasks_done=0,
        total_tasks=SECONDS_TO_WAIT,
    )

    secs_elapsed = 0
    while secs_elapsed < SECONDS_TO_WAIT:
        time.sleep(1)
        secs_elapsed += 1
        set_progress(
            job, tasks_done=secs_elapsed, total_tasks=SECONDS_TO_WAIT, increment_tasks=1
        )

    return "", "", ""
