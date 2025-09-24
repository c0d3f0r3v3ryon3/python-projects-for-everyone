"""
Утилиты для парсинга бинарных данных от SDR-утилит.
Используются в нескольких бэкендах.
"""

import struct
import numpy as np

def parse_binary_header(data: bytes, format_str: str) -> tuple:
    """
    Парсит бинарный заголовок по заданной структуре.
    :param data: байты заголовка
    :param format_str: формат struct (например, '<QQII')
    :return: кортеж значений
    """
    try:
        return struct.unpack(format_str, data)
    except struct.error as e:
        raise ValueError(f"Невозможно распарсить заголовок: {e}")

def parse_binary_rssi_data(data: bytes, count: int) -> np.ndarray:
    """
    Парсит массив значений RSSI из бинарных данных.
    Предполагается формат float32 (little-endian).
    :param data: байты данных
    :param count: количество значений
    :return: numpy array
    """
    if len(data) < count * 4:
        raise ValueError(f"Недостаточно данных: ожидается {count * 4} байт, получено {len(data)}")
    return np.frombuffer(data[:count*4], dtype='<f4')
