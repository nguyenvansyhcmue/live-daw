"""Level and waveform extraction performed away from native audio callbacks."""

from __future__ import annotations

from time import monotonic

import numpy as np

from .models import AudioFrame, LevelSnapshot


class AudioAnalysis:
    """Creates small UI snapshots without storing or recording raw audio."""

    def __init__(self, waveform_points: int = 96, spectrum_points: int = 72):
        if waveform_points < 8:
            raise ValueError("waveform_points must be at least 8")
        if spectrum_points < 8:
            raise ValueError("spectrum_points must be at least 8")
        self.waveform_points = int(waveform_points)
        self.spectrum_points = int(spectrum_points)

    def analyse(self, frame: AudioFrame) -> LevelSnapshot:
        samples = frame.samples
        stereo = samples if frame.channels == 2 else np.repeat(samples, 2, axis=1)
        rms = np.sqrt(np.mean(np.square(stereo, dtype=np.float64), axis=0))
        peaks = np.max(np.abs(stereo), axis=0)
        mono = np.mean(stereo, axis=1)
        # Peak envelope per bucket reads clearly at a small header size.
        edges = np.linspace(0, mono.size, self.waveform_points + 1, dtype=np.int32)
        waveform = np.empty(self.waveform_points, dtype=np.float32)
        for index in range(self.waveform_points):
            bucket = mono[edges[index]:edges[index + 1]]
            waveform[index] = float(np.max(np.abs(bucket))) if bucket.size else 0.0
        spectrum = self._spectrum(mono, frame.sample_rate)
        return LevelSnapshot(
            rms_left=float(rms[0]), rms_right=float(rms[1]),
            peak_left=float(peaks[0]), peak_right=float(peaks[1]),
            waveform=waveform, spectrum=spectrum, timestamp=monotonic(),
        )

    def _spectrum(self, mono: np.ndarray, sample_rate: int) -> np.ndarray:
        """Return bounded log-frequency display bands from captured PCM.

        Analysis is invoked by ``CaptureCoordinator``'s worker, rather than a
        native audio callback.  The values are amplitudes mapped from -90..0
        dBFS to 0..1, which keeps rendering independent of a particular FFT
        size while retaining the actual input's spectral shape.
        """
        if mono.size < 8:
            return np.zeros(self.spectrum_points, dtype=np.float32)
        # Cap the visual FFT cost and use the most recent samples so a slow UI
        # never turns the analyzer into a source of stale data.
        block = np.asarray(mono[-min(mono.size, 4096):], dtype=np.float32)
        window = np.hanning(block.size).astype(np.float32)
        magnitudes = np.abs(np.fft.rfft(block * window))
        frequencies = np.fft.rfftfreq(block.size, d=1.0 / sample_rate)
        high = min(float(sample_rate) * .5, 20_000.0)
        if high <= 20.0:
            return np.zeros(self.spectrum_points, dtype=np.float32)
        edges = np.geomspace(20.0, high, self.spectrum_points + 1)
        result = np.zeros(self.spectrum_points, dtype=np.float32)
        normalizer = max(1.0, float(window.sum()) * .5)
        for index, (low, upper) in enumerate(zip(edges[:-1], edges[1:])):
            band = magnitudes[(frequencies >= low) & (frequencies < upper)]
            amplitude = float(band.max()) / normalizer if band.size else 0.0
            db = 20.0 * np.log10(max(amplitude, 1.0e-9))
            result[index] = np.float32(np.clip((db + 90.0) / 90.0, 0.0, 1.0))
        return result
