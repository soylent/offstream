import logging
import sys

from .scheduler import Scheduler

logger = logging.getLogger("offstream")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

__all__ = ["Scheduler"]
