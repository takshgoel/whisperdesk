"""
recorder.py — Background microphone recording worker for WhisperDesk.

Captures audio from the default input device using sounddevice's callback
(InputStream) mode.  Every CHUNK_DURATION_S seconds the accumulated buffer is
saved to a WAV file and emitted via chunk_ready so the UI can hand it off to a
TranscriberWorker.  Audio levels are emitted ~20 times per second so the level
bar in the UI stays responsive.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class RecorderWorker(QThread):
    """
    QThread that streams microphone audio in 8-second chunks.

    Signals
    -------
    level(float)        — Normalised RMS 0.0–1.0, emitted ~20 × per second.
    chunk_ready(str)    — Absolute path to a saved WAV chunk, emitted every
                          CHUNK_DURATION_S seconds while recording.
    stopped()           — Emitted once after recording has fully stopped.
    error(str)          — Human-readable error on mic permission denied etc.
    """

    level       = pyqtSignal(float)
    chunk_ready = pyqtSignal(str)
    stopped     = pyqtSignal()
    error       = pyqtSignal(str)

    CHUNK_DURATION_S: int   = 8       # seconds per audio chunk
    SAMPLE_RATE:      int   = 16000   # Hz — matches Whisper's expected rate
    CHANNELS:         int   = 1       # mono
    DTYPE:            str   = "int16"

    # Emit a level reading after this many frames accumulate in the callback
    # buffer.  At 16 kHz, 800 frames ≈ 50 ms ≈ 20 emissions per second.
    _LEVEL_FRAMES: int = 800

    def __init__(self, temp_dir: str, parent: Optional[object] = None) -> None:
        """Initialise with the path to the temp directory for chunk files."""
        super().__init__(parent)
        self._temp_dir   = Path(temp_dir)
        self._stop_event = threading.Event()
        self._buffer: list[np.ndarray] = []
        self._buffer_frames: int = 0
        self._chunk_count:   int = 0
        self._level_accum:   list[np.ndarray] = []
        self._stream: Optional[object] = None   # sounddevice.InputStream

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the recording loop to stop and close the audio stream."""
        logger.debug("RecorderWorker.stop() called")
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop()  # type: ignore[union-attr]
            except Exception:
                pass

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Open the audio stream and record until stop() is called."""
        import sounddevice as sd  # noqa: PLC0415 — deferred to worker thread

        self._stop_event.clear()
        self._buffer = []
        self._buffer_frames = 0
        self._chunk_count = 0
        self._level_accum = []

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                callback=self._audio_callback,
                blocksize=self._LEVEL_FRAMES,
            ) as stream:
                self._stream = stream
                logger.info("Audio stream opened (sample_rate=%d)", self.SAMPLE_RATE)
                # Spin until stop() sets the event
                while not self._stop_event.is_set():
                    time.sleep(0.01)

        except Exception as exc:
            # Covers PortAudioError (mic denied), device not found, etc.
            logger.exception("RecorderWorker audio stream error")
            self.error.emit(
                f"Microphone error: {exc}. "
                "Check Windows microphone privacy settings."
            )
        finally:
            self._stream = None
            self._flush_remaining_buffer()
            logger.info("RecorderWorker finished")
            self.stopped.emit()

    # ------------------------------------------------------------------
    # Audio callback — runs on the PortAudio thread, NOT the Qt thread
    # (cross-thread signal emission is safe in PyQt6 via queued connections)
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Accumulate audio frames, emit level, and save chunks periodically."""
        if status:
            logger.debug("Audio callback status: %s", status)

        # Copy frame data (indata is a view into a C buffer that will be recycled)
        chunk = indata.copy()

        # ── Level emission ────────────────────────────────────────────
        self._level_accum.append(chunk)
        accum_frames = sum(a.shape[0] for a in self._level_accum)
        if accum_frames >= self._LEVEL_FRAMES:
            block = np.concatenate(self._level_accum, axis=0)
            rms = float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))
            # int16 max is 32768; scale and clamp to 0-1
            normalised = min(rms / 3276.8, 1.0)   # ~10× amplification
            self.level.emit(normalised)
            self._level_accum = []

        # ── Chunk accumulation ────────────────────────────────────────
        self._buffer.append(chunk)
        self._buffer_frames += frames

        target_frames = self.CHUNK_DURATION_S * self.SAMPLE_RATE
        if self._buffer_frames >= target_frames:
            self._save_and_emit_chunk()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_and_emit_chunk(self) -> None:
        """Write the accumulated buffer to a WAV file and emit chunk_ready."""
        audio = np.concatenate(self._buffer, axis=0)
        self._buffer = []
        self._buffer_frames = 0

        filename = self._temp_dir / f"chunk_{self._chunk_count:04d}.wav"
        self._chunk_count += 1

        try:
            sf.write(str(filename), audio, self.SAMPLE_RATE, subtype="PCM_16")
            logger.debug("Chunk saved: %s (%d frames)", filename, audio.shape[0])
            self.chunk_ready.emit(str(filename))
        except Exception as exc:
            logger.error("Failed to save chunk %s: %s", filename, exc)
            self.error.emit(f"Could not save audio chunk: {exc}")

    def _flush_remaining_buffer(self) -> None:
        """Save any audio frames left in the buffer after stop() is called."""
        if self._buffer_frames > 0:
            logger.debug(
                "Flushing %d remaining frames as final chunk", self._buffer_frames
            )
            self._save_and_emit_chunk()
