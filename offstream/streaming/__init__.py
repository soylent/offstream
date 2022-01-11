import logging
import sys

from .recorder import Recorder

logger = logging.getLogger("offstream")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

__all__ = ["Recorder"]
