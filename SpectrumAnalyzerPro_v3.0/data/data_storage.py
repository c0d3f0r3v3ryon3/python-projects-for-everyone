"""
Централизованное хранилище данных — аналог qspectrumanalyzer.data.DataStorage.
Поддерживает: скользящее среднее, пик-холд, сглаживание, персистентность, базовую линию.
"""

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable
from scipy.signal import savgol_filter
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class HistoryBuffer:
    """Кольцевой буфер для водопада."""
    def __init__(self, max_size: int, data_size: int):
        self.max_size = max_size
        self.data_size = data_size
        self.history_size = 0
        self.buffer = np.full((max_size, data_size), -100.0, dtype=np.float32)
        self.counter = 0

    def append(self, data: np.ndarray):
        if len(data) != self.data_size:
            raise ValueError(f"Ожидается {self.data_size} значений, получено {len(data)}")
        self.counter += 1
        if self.history_size < self.max_size:
            self.history_size += 1
        self.buffer = np.roll(self.buffer, -1, axis=0)
        self.buffer[-1] = data.copy()

    def get_buffer(self) -> np.ndarray:
        return self.buffer[-self.history_size:]


class DataStorage(QObject):
    """Главный менеджер данных для спектра и водопада."""
    data_updated = pyqtSignal(dict)
    history_updated = pyqtSignal(object)
    average_updated = pyqtSignal(dict)
    peak_hold_max_updated = pyqtSignal(dict)
    peak_hold_min_updated = pyqtSignal(dict)
    history_recalculated = pyqtSignal(object)
    baseline_updated = pyqtSignal(dict)  # <-- ДОБАВЛЕНО!

    def __init__(self, max_history_size: int = 100):
        super().__init__()
        self.max_history_size = max_history_size
        self.history = None
        self.x = None
        self.y = None
        self.average = None
        self.peak_hold_max = None
        self.peak_hold_min = None
        self.smooth = False
        self.smooth_length = 11
        self.smooth_window = "hanning"
        self.subtract_baseline = False
        self.baseline = None
        self.baseline_x = None
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)

    def reset(self):
        self.history = None
        self.x = None
        self.y = None
        self.average = None
        self.peak_hold_max = None
        self.peak_hold_min = None
        self.baseline = None
        self.baseline_x = None

    def update(self, sweep: dict):
        """Добавить новый снимок спектра."""
        x = sweep['x']
        y = sweep['y'].copy()

        if self.x is None:
            self.x = x
        elif len(x) != len(self.x):
            logger.warning(f"Изменение числа бинов: {len(self.x)} → {len(x)}. Пропускаем.")
            return

        # Применяем LNB LO уже в бэкенде — здесь только базовая обработка
        if self.subtract_baseline and self.baseline is not None and len(y) == len(self.baseline):
            y = y - self.baseline

        # Обновляем историю
        if self.history is None:
            self.history = HistoryBuffer(self.max_history_size, len(x))
        self.history.append(y)

        # Сглаживание
        y_processed = self._apply_smoothing(y)
        self.y = y_processed
        self.data_updated.emit({'x': self.x, 'y': self.y})

        # Расчет производных в отдельных потоках
        self.threadpool.start(Task(self._update_average, y))
        self.threadpool.start(Task(self._update_peak_hold_max, y))
        self.threadpool.start(Task(self._update_peak_hold_min, y))

        self.history_updated.emit(self)

    def _apply_smoothing(self, y: np.ndarray) -> np.ndarray:
        if not self.smooth:
            return y
        if len(y) < self.smooth_length:
            return y
        return savgol_filter(y, self.smooth_length, 3)

    def _update_average(self, y: np.ndarray):
        if self.average is None:
            self.average = y.copy()
        else:
            self.average = 0.9 * self.average + 0.1 * y
        self.average_updated.emit({'x': self.x, 'y': self.average})

    def _update_peak_hold_max(self, y: np.ndarray):
        if self.peak_hold_max is None:
            self.peak_hold_max = y.copy()
        else:
            self.peak_hold_max = np.maximum(self.peak_hold_max, y)
        self.peak_hold_max_updated.emit({'x': self.x, 'y': self.peak_hold_max})

    def _update_peak_hold_min(self, y: np.ndarray):
        if self.peak_hold_min is None:
            self.peak_hold_min = y.copy()
        else:
            self.peak_hold_min = np.minimum(self.peak_hold_min, y)
        self.peak_hold_min_updated.emit({'x': self.x, 'y': self.peak_hold_min})

    def set_smooth(self, enable: bool, length: int = 11, window: str = "hanning"):
        if self.smooth != enable or self.smooth_length != length or self.smooth_window != window:
            self.smooth = enable
            self.smooth_length = length
            self.smooth_window = window
            self.recalculate_data()

    def set_subtract_baseline(self, enable: bool, baseline_file: str = None):
        self.subtract_baseline = enable
        if baseline_file and os.path.exists(baseline_file):
            # Читаем CSV: freq,db
            data = np.loadtxt(baseline_file, delimiter=',', skiprows=1)
            self.baseline_x = data[:, 0]
            self.baseline = data[:, 1]
            if len(self.baseline) != len(self.x):
                logger.warning(f"Размер базовой линии ({len(self.baseline)}) не совпадает с текущим спектром ({len(self.x)})")
                self.baseline = None
        else:
            self.baseline = None
            self.baseline_x = None
        self.recalculate_data()

    def recalculate_data(self):
        """Пересчитать все кривые с учётом новых настроек."""
        if self.history is None:
            return
        history = self.history.get_buffer()
        if len(history) == 0:
            return
        last = history[-1]
        if self.smooth:
            last = self._apply_smoothing(last)
        self.y = last
        self.average = np.mean(history, axis=0)
        self.peak_hold_max = np.max(history, axis=0)
        self.peak_hold_min = np.min(history, axis=0)
        self.data_updated.emit({'x': self.x, 'y': self.y})
        self.average_updated.emit({'x': self.x, 'y': self.average})
        self.peak_hold_max_updated.emit({'x': self.x, 'y': self.peak_hold_max})
        self.peak_hold_min_updated.emit({'x': self.x, 'y': self.peak_hold_min})
        self.history_recalculated.emit(self)

class Task(QRunnable):
    """Задача для QThreadPool."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)
