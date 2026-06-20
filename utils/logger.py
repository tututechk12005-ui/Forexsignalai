import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE


def setup_logger(name="forex_smc_bot"):
    log = logging.getLogger(name)
    log.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    try:
        fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError:
        pass
    return log


logger = setup_logger()
