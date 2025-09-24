"""
Инициализация модуля управления данными.
Позволяет импортировать классы из data/ через 'from data import *'
"""

from .history_buffer import HistoryBuffer
from .data_storage import DataStorage

__all__ = [
    'HistoryBuffer',
    'DataStorage'
]
