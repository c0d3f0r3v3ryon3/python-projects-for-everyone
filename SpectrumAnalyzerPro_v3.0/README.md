# 📡 SpectrumAnalyzer Pro v3.0 — Универсальный SDR-анализатор

**Объединяет лучшее из вашего проекта, qspectrumanalyzer и soapy_power.**

## 💡 Возможности

- ✅ Поддержка всех популярных SDR-устройств: **RTL-SDR, HackRF, Airspy, LimeSDR, PlutoSDR, SDRplay** (через SoapySDR).
- ✅ Реальное время: спектр, водопад со шкалой уровней (`HistogramLUT`).
- ✅ Автоматическое обнаружение и классификация сигналов (AM, FM, Digital, CW).
- ✅ Запись IQ-данных в `.bin`.
- ✅ Аveraging, Peak Hold, Smoothing, Persistence, Baseline Subtraction.
- ✅ Экспорт в PNG, PDF, CSV, JSON.
- ✅ Темная тема, горячие клавиши, логирование событий.
- ✅ Модульная архитектура — легко добавить новое устройство!

## 🚀 Установка

### 1. Установите зависимости

```bash
pip install PyQt5 numpy scipy pyqtgraph pandas python-soapy
