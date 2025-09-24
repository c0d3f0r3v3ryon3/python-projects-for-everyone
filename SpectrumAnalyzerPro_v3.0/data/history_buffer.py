"""
Кольцевой буфер для хранения истории водопада.
Аналогично qspectrumanalyzer.data.HistoryBuffer, но без зависимостей от DataStorage.
"""

import numpy as np

class HistoryBuffer:
    """Fixed-size NumPy array ring buffer for waterfall history."""
    def __init__(self, max_size: int, data_size: int):
        self.max_size = max_size
        self.data_size = data_size
        self.history_size = 0
        self.counter = 0
        self.buffer = np.full((max_size, data_size), -100.0, dtype=np.float32)

    def append(self, data: np.ndarray):
        """Добавить новый ряд данных в буфер."""
        if len(data) != self.data_size:
            raise ValueError(f"Ожидается {self.data_size} значений, получено {len(data)}")
        self.counter += 1
        if self.history_size < self.max_size:
            self.history_size += 1
        # Сдвигаем буфер влево и записываем в конец
        self.buffer = np.roll(self.buffer, -1, axis=0)
        self.buffer[-1] = data.copy()

    def get_buffer(self) -> np.ndarray:
        """Вернуть только реальные данные (не весь буфер)."""
        if self.history_size < self.max_size:
            return self.buffer[-self.history_size:]
        else:
            return self.buffer
