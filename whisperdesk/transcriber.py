"""
transcriber.py — Background transcription worker for WhisperDesk.

Runs OpenAI Whisper in a QThread so the GUI stays responsive.  Accepts an
audio file path, converts non-WAV formats via ffmpeg, loads (and caches) the
Whisper model, and emits transcription segments one by one as they arrive.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level model cache — shared across TranscriberWorker instances so
# repeated calls with the same model name skip the expensive load step.
# ---------------------------------------------------------------------------
_model_cache: dict[str, Any] = {}
_model_cache_lock = threading.Lock()


class TranscriberWorker(QThread):
    """
    QThread that loads a Whisper model and transcribes a single audio file.

    Signals
    -------
    progress(str)       — Emitted for each transcription segment as it arrives.
    status(str, str)    — (state_key, detail_message) state changes.
    finished(str)       — Full transcript text after all segments are done.
    error(str)          — Human-readable error message on failure.
    """

    progress = pyqtSignal(str)
    status   = pyqtSignal(str, str)
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(
        self,
        audio_path: str,
        model_name: str,
        chunk_index: int = 1,
        chunk_total: int = 1,
        parent: Optional[Any] = None,
    ) -> None:
        """Store transcription parameters; do NOT load the model here."""
        super().__init__(parent)
        self._audio_path  = audio_path
        self._model_name  = model_name
        self._chunk_index = chunk_index
        self._chunk_total = chunk_total
        self._temp_wav: Optional[str] = None   # path to converted WAV, if any

    # ------------------------------------------------------------------
    # Main thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Orchestrate the full transcription pipeline."""
        try:
            self._transcribe()
        except Exception as exc:
            logger.exception("Unhandled error in TranscriberWorker")
            self.error.emit(str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transcribe(self) -> None:
        """Load model, convert audio if needed, transcribe, and emit segments."""
        chunk_label = f"chunk {self._chunk_index} of {self._chunk_total}"

        # ── Step 1: resolve WAV path ──────────────────────────────────
        audio_path = Path(self._audio_path)
        if not audio_path.exists():
            self.error.emit(f"Audio file not found: {audio_path}")
            return

        self.status.emit("processing", f"Preparing audio… ({chunk_label})")
        if audio_path.suffix.lower() != ".wav":
            try:
                wav_path = self._convert_to_wav(str(audio_path))
                self._temp_wav = wav_path
            except FileNotFoundError:
                self.error.emit(
                    "ffmpeg not found. Install ffmpeg and add it to PATH."
                )
                return
            except RuntimeError as exc:
                self.error.emit(str(exc))
                return
        else:
            wav_path = str(audio_path)

        # ── Step 2: load Whisper model (cached) ──────────────────────
        self.status.emit("processing", f"Loading model '{self._model_name}'…")
        model = self._get_model(self._model_name)

        # ── Step 3: load audio as numpy array ────────────────────────
        # We load the WAV ourselves with soundfile so we never call Whisper's
        # internal load_audio(), which requires ffmpeg even for .wav files.
        self.status.emit("processing", f"Loading audio… ({chunk_label})")
        import soundfile as sf  # noqa: PLC0415
        import numpy as np      # noqa: PLC0415

        audio_data, sample_rate = sf.read(wav_path, dtype="float32")
        # Mix down to mono if stereo
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        # Resample to 16 kHz if needed (Whisper requirement)
        if sample_rate != 16000:
            from scipy import signal as sp_signal  # noqa: PLC0415
            target_len = int(len(audio_data) * 16000 / sample_rate)
            audio_data = sp_signal.resample(audio_data, target_len).astype(np.float32)

        # ── Step 4: transcribe ────────────────────────────────────────
        self.status.emit("processing", f"Transcribing… ({chunk_label})")

        # Import whisper here (not at module top) to avoid a 3-4 s startup
        # delay on the main thread while the torch/whisper libs load.
        import whisper  # noqa: PLC0415

        logger.debug("Starting transcription of %s (array shape %s)", wav_path, audio_data.shape)
        result: dict = model.transcribe(
            audio_data,          # numpy float32 array — no ffmpeg needed
            verbose=False,
            language="en",
            fp16=False,          # CPU inference; fp16 only helps on GPU
        )

        # ── Step 5: emit segments ────────────────────────────────────
        segments = result.get("segments", [])
        full_text_parts: list[str] = []

        for segment in segments:
            text = segment.get("text", "").strip()
            if text:
                full_text_parts.append(text)
                self.progress.emit(text + " ")

        full_text = " ".join(full_text_parts)
        logger.debug("Transcription done — %d chars", len(full_text))
        self.finished.emit(full_text)
        self.status.emit("done", "")

        # ── Step 6: clean up temp file ────────────────────────────────
        if self._temp_wav:
            try:
                Path(self._temp_wav).unlink(missing_ok=True)
            except OSError:
                pass

    def _convert_to_wav(self, input_path: str) -> str:
        """
        Convert an audio file to 16 kHz mono PCM WAV using ffmpeg.

        Returns the path to the output WAV file.
        Raises FileNotFoundError if ffmpeg is not on PATH.
        Raises RuntimeError on non-zero ffmpeg exit code.
        """
        # Derive a temp output path next to the input file
        out_path = str(Path(input_path).with_suffix("")) + "_converted.wav"
        cmd = [
            "ffmpeg",
            "-y",                  # overwrite without asking
            "-i", input_path,
            "-ar", "16000",        # 16 kHz sample rate (Whisper requirement)
            "-ac", "1",            # mono
            "-c:a", "pcm_s16le",   # 16-bit little-endian PCM
            out_path,
        ]
        logger.debug("Running ffmpeg: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            timeout=300,
        )
        if result.returncode != 0:
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ffmpeg conversion failed (exit {result.returncode}):\n"
                + stderr_text[:600]
            )
        return out_path

    def _get_model(self, model_name: str) -> Any:
        """Return a cached Whisper model, loading it on first call."""
        import whisper  # noqa: PLC0415

        with _model_cache_lock:
            if model_name not in _model_cache:
                logger.info("Loading Whisper model '%s'", model_name)
                t0 = time.monotonic()
                _model_cache[model_name] = whisper.load_model(model_name)
                logger.info(
                    "Model '%s' loaded in %.1fs",
                    model_name,
                    time.monotonic() - t0,
                )
            return _model_cache[model_name]
