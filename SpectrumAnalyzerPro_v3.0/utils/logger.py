"""
Простой логгер с таймстампами.
Используется везде, где нужен вывод в лог-окно.
"""

import logging
from datetime import datetime

def get_logger(name: str = "SpectrumAnalyzer") -> logging.Logger:
    """Создает и настраивает логгер."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
