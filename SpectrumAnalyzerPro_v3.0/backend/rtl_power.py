"""
Бэкенд для RTL-SDR через rtl_power (текстовый вывод).
Совместим с вашей текущей реализацией, но интегрирован в новую архитектуру.
"""

import os
import numpy as np
from datetime import datetime
from PyQt5.QtCore import QProcess
from .base import BackendInfo, BackendPowerThread

class RtlPowerInfo(BackendInfo):
    cmd = "rtl_power"
    args_template = [
        "-f", "{start}M:{end}M:{step}k",
        "-i", "{interval}",
        "-g", "{gain}",
        "-1", "-"
    ]
    hint_range = (24, 1766)
    hint_step = "1–2500 кГц"
    default_gain = 30
    output_type = "text"

    @classmethod
    def help_device(cls, executable: str, device: str) -> str:
        return (
            "Для RTL-SDR: Убедитесь, что драйвер установлен.\n"
            "Используйте команду 'rtl_test' для проверки работы устройства.\n"
            "Рекомендуется использовать форк Keenerd (https://github.com/keenerd/rtl-sdr)."
        )

class RtlPowerThread(BackendPowerThread):
    def __init__(self, *args, **kwargs):
        super().__init__(RtlPowerInfo(), *args, **kwargs)

    def setup(self):
        self.params = {
            "start": self.start_freq,
            "end": self.end_freq,
            "step": self.step,
            "gain": self.gain,
            "interval": self.interval,
        }

    def process_start(self):
        """Запускаем rtl_power напрямую без bash -c."""
        args = [arg.format(**self.params) for arg in self.info.args_template]
        self.process = QProcess()
        self.process.setProgram(self.info.cmd)
        self.process.setArguments(args)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start()
        if not self.process.waitForStarted(5000):
            raise RuntimeError(f"Не удалось запустить {self.info.cmd}")

    def parse_output(self, line: str):
        """Парсим текстовый вывод rtl_power."""
        parts = line.split(',')
        # Проверяем, что это строка с данными (первый элемент — число)
        if len(parts) >= 8 and parts[0].strip().replace('-', '').isdigit():
            try:
                start_freq = float(parts[2])
                step_hz = float(parts[4])
                num_steps = int(parts[5])
                db_values = list(map(float, parts[6:6 + num_steps]))
                frequencies = [start_freq + i * step_hz for i in range(num_steps)]
                self.data_updated.emit({
                    'x': np.array(frequencies),
                    'y': np.array(db_values),
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
            except Exception as e:
                self.log_message.emit(f"Ошибка парсинга rtl_power: {e}")
                return
