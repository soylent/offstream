import logging
import sys

from .recorder import Recorder

logger = logging.getLogger("offstream")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

__all__ = ["Recorder"]
