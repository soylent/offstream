import logging
import sys

from .scheduler import Scheduler

logger = logging.getLogger("offstream")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

__all__ = ["Scheduler"]
