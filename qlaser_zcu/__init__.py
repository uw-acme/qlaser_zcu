import sys
from loguru import logger

logger.remove()  # Remove the default handler.
LOGGER_ID_FILE = logger.add("qlaser.log", level="DEBUG", format="[{time:HH:mm:ss} {level}] [{file}:{line}]: {message}", compression="zip", backtrace=True,)  # File handler logger ID.
LOGGER_ID_CONSOLE = logger.add(sys.stderr, level="INFO", format="[<green>{time:HH:mm:ss}</green> <level>{level}</level>]: <level>{message}</level>", colorize=True)  # Console handler logger ID.
