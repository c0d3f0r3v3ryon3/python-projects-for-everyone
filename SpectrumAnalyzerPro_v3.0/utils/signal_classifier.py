import numpy as np
from scipy.signal import find_peaks

class SignalClassifier:
    def __init__(self):
        pass

    def zero_crossing_rate(self, y):
        return np.sum(np.abs(np.diff(np.signbit(y)))) / (2 * len(y))

    def detect_modulation_around_peak(self, db_values, peak_idx, window=50):
        start = max(0, peak_idx - window//2)
        end = min(len(db_values), peak_idx + window//2)
        segment = db_values[start:end]
        if len(segment) < 10:
            return "Unknown"
        variance = np.var(segment)
        zcr = self.zero_crossing_rate(segment)
        N = len(segment)
        if N > 16:
            spec = np.abs(np.fft.fft(segment - np.mean(segment))[:N//2])
            spec = spec / (np.sum(spec) + 1e-10)
            entropy = -np.sum(spec * np.log2(spec + 1e-10))
        else:
            entropy = 0

        if variance > 15 and zcr > 0.3:
            return "Digital"
        elif variance > 8 and entropy > 2.0:
            return "FM"
        elif variance < 5 and entropy < 1.5:
            return "AM"
        elif zcr > 0.4:
            return "FSK/PSK"
        else:
            return "Unknown"

    def classify_signal(self, modulation, bandwidth_mhz):
        if modulation == "AM":
            if bandwidth_mhz < 0.01:
                return "AM Narrowband (Aviation, Ham)"
            elif bandwidth_mhz < 0.1:
                return "AM Broadcast (MW/SW)"
            else:
                return "AM Wideband"
        elif modulation == "FM":
            if 0.05 < bandwidth_mhz < 0.25:
                return "FM Broadcast"
            elif bandwidth_mhz < 0.03:
                return "NBFM (Radio Amateur)"
            else:
                return "Wide FM"
        elif modulation == "Digital":
            if bandwidth_mhz < 0.02:
                return "LoRa / Sigfox"
            elif bandwidth_mhz < 0.2:
                return "DMR / D-STAR / NXDN"
            elif bandwidth_mhz < 1.0:
                return "DAB / ATSC / DVB-T"
            else:
                return "Wideband Digital"
        elif modulation == "FSK/PSK":
            if bandwidth_mhz < 0.05:
                return "AX.25 / RTTY / FSK"
            else:
                return "PSK31 / QPSK"
        else:
            if bandwidth_mhz < 0.01:
                return "CW / Beacon"
            else:
                return "Unknown Signal"
