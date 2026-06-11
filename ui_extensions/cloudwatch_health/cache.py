"""Read/write the pre-computed CloudWatch snapshot.

The recurring job writes the snapshot (admin context, all servers); views read
it and filter to the requesting user's RBAC scope. Falls back to a live pull
when the snapshot is missing or stale.
"""

import json
import os
import time

from utilities.logger import ThreadLogger

from xui.cloudwatch_health import constants

logger = ThreadLogger(__name__)

_PATH = os.path.join(constants.CACHE_DIR, constants.CACHE_FILE)


def write_snapshot(data):
    """Write the snapshot atomically."""
    os.makedirs(constants.CACHE_DIR, exist_ok=True)
    tmp = f"{_PATH}.tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, _PATH)
    logger.info(f"Wrote CloudWatch snapshot to {_PATH}")


def read_snapshot():
    """Return (data, age_seconds) or (None, None) if absent/unreadable."""
    try:
        age = time.time() - os.path.getmtime(_PATH)
        with open(_PATH, "r") as fh:
            return json.load(fh), age
    except (OSError, ValueError) as err:
        logger.debug(f"No usable CloudWatch snapshot: {err}")
        return None, None


def is_fresh(age_seconds):
    return age_seconds is not None and age_seconds <= constants.CACHE_MAX_AGE_SECONDS
