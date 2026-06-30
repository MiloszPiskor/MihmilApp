"""
Central logging configuration for PrexpolAppZkVo.
"""
import logging
import sys
from pathlib import Path

# Ścieżka do logów
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "app.log"

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Konfiguruje logger z konsolą i plikiem.

    Args:
        name: Nazwa loggera (zazwyczaj __name__ z modułu)
        level: Poziom logowania (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Skonfigurowany logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Unikaj dublowania handlerów
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler do konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler do pliku
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """Pobiera/konfiguruje logger."""
    return setup_logger(name)
