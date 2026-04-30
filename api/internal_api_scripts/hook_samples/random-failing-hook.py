import random

from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(*args, **kwargs):
    logger.info("This hook will randomly fail 50% of the time")
    if random.randrange(2):
        return "FAILURE", "", "This hook failed"
    else:
        return "", "This hook succeeded", ""
