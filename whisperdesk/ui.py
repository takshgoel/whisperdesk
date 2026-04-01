"""
ui.py — Main window and all custom widgets for WhisperDesk.

Contains:
  WaveformIcon        — Programmatically painted waveform / audio-bars icon.
  AudioLevelWidget    — Animated horizontal level bar updated from mic signal.
  DropZoneWidget      — Drag-and-drop / click-to-browse file selector.
  ModeToggle          — Animated pill toggle (Microphone ↔ File).
  StatusBar           — Custom status frame with animated state dot.
  TitleBar            — Custom frameless-window drag handle + controls.
  MainWindow          — Root window; wires all workers and widgets together.
"""

import datetime
import logging
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPixmap,
    QTextBlockFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from styles import (
    ACCENT,
    BG,
    BORDER,
    BORDER_STRONG,
    FONT_MONO,
    FONT_SANS,
    GREEN,
    GREEN_BG,
    GREEN_BORDER,
    MUTED_BG,
    RED_RECORD,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    APP_VERSION,
)
from transcriber import TranscriberWorker
from recorder import RecorderWorker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# All user-visible text in one place
# ---------------------------------------------------------------------------
STRINGS: dict[str, str] = {
    "app_name":          "WhisperDesk",
    "version":           f"v{APP_VERSION}",
    "model_label":       "Model:",
    "section_input":     "INPUT",
    "section_transcript":"TRANSCRIPT",
    "mode_mic":          "Microphone",
    "mode_file":         "File",
    "record_idle":       "  Start Recording",
    "record_active":     "  Stop Recording",
    "transcribe_btn":    "Transcribe File",
    "drop_hint1":        "Drop audio file here",
    "drop_hint2":        "or click to browse",
    "drop_formats":      "MP3 · WAV · M4A · OGG",
    "copy_btn":          "Copy",
    "copy_done":         "Copied ✓",
    "save_btn":          "Save .txt",
    "clear_btn":         "Clear",
    "clear_title":       "Clear transcript?",
    "clear_body":        "This will permanently delete the current transcript.",
    "clear_confirm":     "Clear",
    "clear_cancel":      "Cancel",
    "placeholder":       "Your transcript will appear here…",
    "words_zero":        "0 words",
    "powered_by":        "Powered by OpenAI Whisper",
    "runs_local":        "Runs 100% on your machine",
    "status_idle":       "Idle",
    "status_recording":  "Recording…",
    "status_processing": "Processing…",
    "status_done":       "Done — transcript ready",
    "status_error":      "Error",
    "err_no_file":       "No file selected",
    "err_empty_save":    "Transcript is empty — nothing to save",
    "err_empty_copy":    "Transcript is empty",
    "saved_msg":         "Saved to ",
}

ACCEPTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


# ===========================================================================
# WaveformIcon
# ===========================================================================

class WaveformIcon(QWidget):
    """
    A small programmatically drawn waveform (vertical bars) icon.

    bar_heights — list of bar heights in pixels relative to the icon size.
    color       — fill color of the bars.
    """

    _BAR_HEIGHTS_RATIO = [0.30, 0.65, 0.50, 0.90, 0.40]
    _BAR_WIDTH = 2
    _BAR_GAP   = 2

    def __init__(
        self,
        size: int = 20,
        color: str = TEXT_PRIMARY,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Create a waveform icon of the given pixel size."""
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Draw vertical bars centered in the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)

        n = len(self._BAR_HEIGHTS_RATIO)
        total_w = n * self._BAR_WIDTH + (n - 1) * self._BAR_GAP
        x_start = (self.width() - total_w) // 2

        for i, ratio in enumerate(self._BAR_HEIGHTS_RATIO):
            bar_h = max(2, int(self.height() * ratio))
            x = x_start + i * (self._BAR_WIDTH + self._BAR_GAP)
            y = (self.height() - bar_h) // 2
            painter.drawRoundedRect(x, y, self._BAR_WIDTH, bar_h, 1, 1)

        painter.end()


def _make_app_icon() -> QIcon:
    """Build a 32×32 QIcon with a white waveform on a dark background."""
    px = QPixmap(32, 32)
    px.fill(QColor(TEXT_PRIMARY))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FFFFFF"))

    heights = [8, 18, 14, 24, 10]
    bar_w, gap = 3, 2
    n = len(heights)
    total_w = n * bar_w + (n - 1) * gap
    x = (32 - total_w) // 2
    for h in heights:
        y = (32 - h) // 2
        painter.drawRoundedRect(x, y, bar_w, h, 1, 1)
        x += bar_w + gap

    painter.end()
    return QIcon(px)


# ===========================================================================
# AudioLevelWidget
# ===========================================================================

class AudioLevelWidget(QWidget):
    """
    A thin horizontal bar that visualises microphone input level.

    Filled from left; fill width proportional to `_level` (0.0–1.0).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialise with zero level."""
        super().__init__(parent)
        self.setFixedHeight(6)
        self._level: float = 0.0

    def set_level(self, level: float) -> None:
        """Update the displayed level and trigger a repaint."""
        self._level = max(0.0, min(1.0, level))
        self.update()

    def reset(self) -> None:
        """Reset level to zero."""
        self.set_level(0.0)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Draw background track and filled portion."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Background track
        painter.setBrush(QColor(BORDER))
        painter.drawRoundedRect(self.rect(), 3, 3)

        # Filled portion
        if self._level > 0.001:
            filled_w = max(6, int(self.width() * self._level))
            painter.setBrush(QColor(GREEN))
            painter.drawRoundedRect(QRect(0, 0, filled_w, self.height()), 3, 3)

        painter.end()


# ===========================================================================
# DropZoneWidget
# ===========================================================================

class DropZoneWidget(QFrame):
    """
    A file drop target that also opens a file dialog on click.

    Emits file_selected(path: str) when a valid audio file is chosen.
    """

    file_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Set up layout and enable drops."""
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setFixedHeight(120)
        self.setMinimumWidth(200)

        self._current_file: Optional[str] = None
        self._reject_timer = QTimer(self)
        self._reject_timer.setSingleShot(True)
        self._reject_timer.timeout.connect(self._end_reject_flash)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the inner label stack."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(2)
        layout.setContentsMargins(12, 12, 12, 12)

        # Upload arrow icon (drawn via a small WaveformIcon reuse — or a QLabel)
        self._icon_label = QLabel("↑")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont(FONT_SANS, 20)
        self._icon_label.setFont(icon_font)
        self._icon_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")

        self._hint1 = QLabel(STRINGS["drop_hint1"])
        self._hint1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint1.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;"
        )

        self._hint2 = QLabel(STRINGS["drop_hint2"])
        self._hint2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint2.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 12px; color: {TEXT_MUTED}; background: transparent;"
        )

        self._formats = QLabel(STRINGS["drop_formats"])
        self._formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._formats.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 11px; color: {TEXT_MUTED};"
            " margin-top: 6px; background: transparent;"
        )

        # ── File-accepted state labels (hidden by default) ──────────
        self._check_label = QLabel("✓")
        self._check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {GREEN}; background: transparent;"
        )
        self._check_label.hide()

        self._file_name_label = QLabel()
        self._file_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_name_label.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 13px; font-weight: 500;"
            f" color: {GREEN}; background: transparent;"
        )
        self._file_name_label.hide()

        self._file_size_label = QLabel()
        self._file_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_size_label.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 11px; color: {TEXT_SECONDARY}; background: transparent;"
        )
        self._file_size_label.hide()

        # Clear button (×) pinned top-right via absolute positioning
        self._clear_btn = QPushButton("×", self)
        self._clear_btn.setFixedSize(18, 18)
        self._clear_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; color: {TEXT_MUTED};"
            f" font-size: 14px; font-weight: bold; border-radius: 9px; padding: 0; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background: {BORDER}; }}"
        )
        self._clear_btn.hide()
        self._clear_btn.clicked.connect(self.clear_file)

        for w in [
            self._icon_label, self._hint1, self._hint2, self._formats,
            self._check_label, self._file_name_label, self._file_size_label,
        ]:
            layout.addWidget(w)

    def resizeEvent(self, event):  # noqa: N802
        """Keep the clear button pinned to top-right corner."""
        self._clear_btn.move(self.width() - 22, 4)
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear_file(self) -> None:
        """Reset to the empty / prompt state."""
        self._current_file = None
        self._set_normal_state()

    def current_file(self) -> Optional[str]:
        """Return the currently selected file path, or None."""
        return self._current_file

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _set_normal_state(self) -> None:
        """Show drop-prompt UI, hide file-info UI."""
        self.setObjectName("dropZone")
        self._refresh_style()
        self._icon_label.show()
        self._hint1.show()
        self._hint2.show()
        self._formats.show()
        self._check_label.hide()
        self._file_name_label.hide()
        self._file_size_label.hide()
        self._clear_btn.hide()

    def _set_accepted_state(self, path: str) -> None:
        """Show file-info UI with green styling."""
        self._current_file = path
        self.setObjectName("dropZoneAccepted")
        self._refresh_style()

        p = Path(path)
        # Truncate long names
        name = p.name if len(p.name) <= 28 else p.name[:25] + "…"
        try:
            size_bytes = p.stat().st_size
            size_str = (
                f"{size_bytes / 1_048_576:.1f} MB"
                if size_bytes >= 1_048_576
                else f"{size_bytes / 1024:.0f} KB"
            )
        except OSError:
            size_str = ""

        self._icon_label.hide()
        self._hint1.hide()
        self._hint2.hide()
        self._formats.hide()
        self._check_label.show()
        self._file_name_label.setText(name)
        self._file_name_label.show()
        self._file_size_label.setText(size_str)
        self._file_size_label.show()
        self._clear_btn.show()

    def _set_rejected_state(self) -> None:
        """Flash red for 600 ms then revert."""
        self.setObjectName("dropZoneRejected")
        self._refresh_style()
        self._reject_timer.start(600)

    def _end_reject_flash(self) -> None:
        """Revert from rejected flash back to normal."""
        self._set_normal_state()

    def _refresh_style(self) -> None:
        """Force QSS re-evaluation after objectName change."""
        self.style().unpolish(self)
        self.style().polish(self)

    # ------------------------------------------------------------------
    # Drag-and-drop event handlers
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Accept drag if it carries a valid audio file URL."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                ext = Path(urls[0].toLocalFile()).suffix.lower()
                if ext in ACCEPTED_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setObjectName("dropZoneDrag")
                    self._refresh_style()
                    return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        """Revert styling when drag leaves the widget."""
        if self._current_file:
            self.setObjectName("dropZoneAccepted")
        else:
            self.setObjectName("dropZone")
        self._refresh_style()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Accept the dropped file."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            ext = Path(path).suffix.lower()
            if ext in ACCEPTED_EXTENSIONS:
                self._set_accepted_state(path)
                self.file_selected.emit(path)
                return
        self._set_rejected_state()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Open a file browser on left-click."""
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Audio File",
                "",
                "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac)",
            )
            if path:
                ext = Path(path).suffix.lower()
                if ext in ACCEPTED_EXTENSIONS:
                    self._set_accepted_state(path)
                    self.file_selected.emit(path)
                else:
                    self._set_rejected_state()


# ===========================================================================
# ModeToggle
# ===========================================================================

class ModeToggle(QWidget):
    """
    Pill-shaped two-option toggle (Microphone / File).

    An animated indicator slides underneath the active option.
    Emits mode_changed(int) with 0 = Microphone, 1 = File.
    """

    mode_changed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build pill container with two buttons and a sliding indicator."""
        super().__init__(parent)
        self._current_index = 0
        self._anim: Optional[QPropertyAnimation] = None

        self.setObjectName("modeToggle")
        self.setFixedHeight(38)
        self.setStyleSheet(
            f"QWidget#modeToggle {{ background-color: {BORDER}; border-radius: 9px; }}"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(3, 3, 3, 3)
        outer.setSpacing(0)

        # Sliding background indicator (lives inside this widget)
        self._indicator = QWidget(self)
        self._indicator.setObjectName("modeIndicator")
        self._indicator.setStyleSheet(
            f"background-color: {SURFACE}; border-radius: 6px;"
        )
        shadow = QGraphicsDropShadowEffect(self._indicator)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 30))
        self._indicator.setGraphicsEffect(shadow)
        self._indicator.lower()   # draw below buttons

        self._btn_mic  = QPushButton(STRINGS["mode_mic"],  self)
        self._btn_file = QPushButton(STRINGS["mode_file"], self)
        for btn in (self._btn_mic, self._btn_file):
            btn.setObjectName("modeBtnActive" if btn is self._btn_mic else "modeBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; }"
            )

        self._btn_mic.clicked.connect(lambda: self._select(0))
        self._btn_file.clicked.connect(lambda: self._select(1))

        outer.addWidget(self._btn_mic)
        outer.addWidget(self._btn_file)

    def showEvent(self, event) -> None:  # noqa: N802
        """Position indicator correctly once the widget has a real size."""
        super().showEvent(event)
        self._place_indicator(self._current_index, animate=False)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Reposition indicator when the toggle is resized."""
        super().resizeEvent(event)
        self._place_indicator(self._current_index, animate=False)

    def _select(self, index: int) -> None:
        """Animate indicator to the chosen index and emit mode_changed."""
        if index == self._current_index:
            return
        self._current_index = index
        self._place_indicator(index, animate=True)
        self._btn_mic.setObjectName(
            "modeBtnActive" if index == 0 else "modeBtn"
        )
        self._btn_file.setObjectName(
            "modeBtnActive" if index == 1 else "modeBtn"
        )
        # Refresh QSS for both buttons
        for btn in (self._btn_mic, self._btn_file):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.mode_changed.emit(index)

    def _place_indicator(self, index: int, animate: bool = True) -> None:
        """Move or animate the sliding indicator to the given slot."""
        if self.width() == 0:
            return
        pad = 3
        slot_w = (self.width() - 2 * pad) // 2
        slot_h = self.height() - 2 * pad
        target = QPoint(pad + index * slot_w, pad)
        self._indicator.resize(slot_w, slot_h)

        if animate:
            # Stop previous animation safely — the C++ object may already be
            # gone if DeleteWhenStopped was used, so guard with try/except.
            if self._anim is not None:
                try:
                    self._anim.stop()
                except RuntimeError:
                    pass
                self._anim = None

            # Keep the animation as a child of self so Qt doesn't delete it
            # while we still hold a reference to it.
            anim = QPropertyAnimation(self._indicator, b"pos", self)
            anim.setDuration(200)
            anim.setEndValue(target)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            anim.start()
            self._anim = anim
        else:
            self._indicator.move(target)


# ===========================================================================
# StatusBar
# ===========================================================================

class StatusBar(QFrame):
    """
    Custom status bar showing state dot + text and elapsed-time counter.

    States: idle | recording | processing | done | error
    """

    _STATE_COLORS = {
        "idle":       TEXT_MUTED,
        "recording":  RED_RECORD,
        "processing": GREEN,
        "done":       GREEN,
        "error":      "#E24B4A",
    }
    _STATE_TEXTS = {
        "idle":       STRINGS["status_idle"],
        "recording":  STRINGS["status_recording"],
        "processing": STRINGS["status_processing"],
        "done":       STRINGS["status_done"],
        "error":      STRINGS["status_error"],
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the status frame with dot, label, and elapsed counter."""
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(28)

        self._elapsed_start: float = 0.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        # Animated dot
        self._dot = QLabel("●")
        self._dot.setStyleSheet(
            f"font-size: 10px; color: {TEXT_MUTED}; background: transparent;"
        )
        self._dot_effect = QGraphicsOpacityEffect(self._dot)
        self._dot.setGraphicsEffect(self._dot_effect)
        self._dot_anim = QPropertyAnimation(self._dot_effect, b"opacity")
        self._dot_anim.setLoopCount(-1)

        # State label
        self._label = QLabel(STRINGS["status_idle"])
        self._label.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 11px;"
            f" color: {TEXT_SECONDARY}; background: transparent;"
        )

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()

        # Elapsed time (right side, hidden except during processing)
        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 11px;"
            f" color: {TEXT_MUTED}; background: transparent;"
        )
        self._elapsed_label.hide()
        layout.addWidget(self._elapsed_label)

        # Timer for updating elapsed label every 100 ms
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(100)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

    def set_state(self, state: str, message: str = "") -> None:
        """Switch to the given state, updating dot color, text, and animation."""
        self._dot_anim.stop()
        self._elapsed_timer.stop()
        self._elapsed_label.hide()
        self._dot_effect.setOpacity(1.0)

        color = self._STATE_COLORS.get(state, TEXT_MUTED)
        self._dot.setStyleSheet(
            f"font-size: 10px; color: {color}; background: transparent;"
        )

        text = message if message else self._STATE_TEXTS.get(state, state)
        self._label.setText(text)

        if state == "recording":
            self._dot_anim.setDuration(700)
            self._dot_anim.setStartValue(0.3)
            self._dot_anim.setEndValue(1.0)
            self._dot_anim.start()

        elif state == "processing":
            self._elapsed_start = time.monotonic()
            self._elapsed_label.setText("0.0s")
            self._elapsed_label.show()
            self._elapsed_timer.start()

    def set_error(self, message: str) -> None:
        """Show an error state with a custom message."""
        self.set_state("error", f"{STRINGS['status_error']}: {message}")

    def _update_elapsed(self) -> None:
        """Refresh the elapsed-time label."""
        elapsed = time.monotonic() - self._elapsed_start
        self._elapsed_label.setText(f"{elapsed:.1f}s")


# ===========================================================================
# TitleBar
# ===========================================================================

class TitleBar(QFrame):
    """
    Frameless-window title bar with drag support.

    Contains the waveform icon, app name, version badge, and model selector.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the title bar layout."""
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self._drag_pos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # ── Left: icon + name + version ──────────────────────────────
        icon_widget = WaveformIcon(size=20, color=TEXT_PRIMARY, parent=self)
        layout.addWidget(icon_widget)
        layout.addSpacing(8)

        name_label = QLabel(STRINGS["app_name"])
        name_label.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 13px; font-weight: 500;"
            f" color: {TEXT_PRIMARY}; background: transparent;"
        )
        layout.addWidget(name_label)
        layout.addSpacing(8)

        ver_label = QLabel(STRINGS["version"])
        ver_label.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 11px;"
            f" color: {TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(ver_label)
        layout.addStretch()

        # ── Right: model label + combo ────────────────────────────────
        model_lbl = QLabel(STRINGS["model_label"])
        model_lbl.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 12px;"
            f" color: {TEXT_SECONDARY}; background: transparent;"
        )
        layout.addWidget(model_lbl)
        layout.addSpacing(6)

        self._model_combo = QComboBox()
        self._model_combo.setObjectName("modelSelector")
        self._model_combo.addItems(["tiny", "base", "small"])
        self._model_combo.setCurrentText("base")
        self._model_combo.setFixedWidth(90)
        self._model_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._model_combo)

    def model_name(self) -> str:
        """Return the currently selected Whisper model name."""
        return self._model_combo.currentText()

    # ------------------------------------------------------------------
    # Frameless window dragging
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Record start position for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self.window().frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Move the window when dragging the title bar."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.window().move(
                event.globalPosition().toPoint() - self._drag_pos
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Clear drag position on release."""
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Maximize / restore on double-click."""
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()


# ===========================================================================
# MainWindow
# ===========================================================================

class MainWindow(QWidget):
    """
    Root application window.

    Hosts the title bar, left input panel, right transcript panel, and status
    bar.  Wires together RecorderWorker and TranscriberWorker instances.
    """

    # Max simultaneous TranscriberWorker threads
    _MAX_CONCURRENT_WORKERS = 2

    def __init__(self, temp_dir: str, parent: Optional[QWidget] = None) -> None:
        """Build the window layout and connect all signals."""
        super().__init__(parent)
        self._temp_dir = temp_dir

        # ── Worker state ──────────────────────────────────────────────
        self._recorder:          Optional[RecorderWorker]      = None
        self._active_workers:    list[TranscriberWorker]        = []
        self._pending_chunks:    list[tuple[str, int]]          = []  # (path, idx)
        self._is_recording:      bool                           = False
        self._chunk_total:       int                            = 0
        self._chunks_done:       int                            = 0
        self._current_file_path: Optional[str]                 = None

        # ── Pulse animation for record button dot ─────────────────────
        self._pulse_anim:   Optional[QPropertyAnimation]        = None
        self._pulse_effect: Optional[QGraphicsOpacityEffect]    = None
        self._rec_duration_timer = QTimer(self)
        self._rec_duration_timer.setInterval(1000)
        self._rec_duration_timer.timeout.connect(self._update_rec_duration)
        self._rec_seconds: int = 0

        self._build_ui()
        self._connect_signals()
        self._apply_window_flags()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _apply_window_flags(self) -> None:
        """Configure frameless window with standard resize/taskbar behaviour."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowTitle(STRINGS["app_name"])
        self.setWindowIcon(_make_app_icon())
        self.setMinimumSize(860, 580)
        self.resize(960, 620)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all widgets into the window layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar(self)
        root.addWidget(self._title_bar)

        # Body: splitter between input panel and transcript panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_input_panel())
        splitter.addWidget(self._build_transcript_panel())
        splitter.setSizes([300, 640])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.handle(1).setEnabled(True)
        root.addWidget(splitter, stretch=1)

        # Status bar
        self._status_bar = StatusBar(self)
        root.addWidget(self._status_bar)

    def _build_input_panel(self) -> QWidget:
        """Construct the left input panel with mode toggle and stacked pages."""
        panel = QWidget()
        panel.setObjectName("inputPanel")
        panel.setMinimumWidth(240)
        panel.setMaximumWidth(360)
        # Use scoped selector so child widgets aren't affected
        panel.setStyleSheet(
            f"QWidget#inputPanel {{ background-color: {BG}; border-right: 1px solid {BORDER}; }}"
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Section label
        section_lbl = QLabel(STRINGS["section_input"])
        section_lbl.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 11px; font-weight: 500;"
            f" letter-spacing: 1px; color: {TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(section_lbl)
        layout.addSpacing(14)

        # Mode toggle
        self._mode_toggle = ModeToggle(panel)
        layout.addWidget(self._mode_toggle)
        layout.addSpacing(16)

        # Stacked pages: 0 = Mic, 1 = File
        self._stack = QStackedWidget()
        # stretch=1 so the stack expands to fill vertical space
        layout.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._build_mic_page())
        self._stack.addWidget(self._build_file_page())

        self._build_input_footer(layout)

        return panel

    def _build_mic_page(self) -> QWidget:
        """Build the Microphone mode page."""
        page = QWidget()
        page.setObjectName("micPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Record button — added directly (no wrapper needed)
        self._record_btn = QPushButton(STRINGS["record_idle"])
        self._record_btn.setObjectName("recordBtnIdle")
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setFixedHeight(48)
        self._record_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._record_btn)

        # Pulsing dot (absolutely positioned inside button via overlay)
        self._pulse_dot = QLabel("●", self._record_btn)
        self._pulse_dot.setStyleSheet(
            "font-size: 10px; color: #FFFFFF; background: transparent;"
        )
        self._pulse_dot.setFixedSize(14, 14)
        self._pulse_dot.hide()

        layout.addSpacing(12)

        # Level bar
        self._level_widget = AudioLevelWidget()
        layout.addWidget(self._level_widget)
        layout.addSpacing(10)

        # Duration label
        self._duration_label = QLabel("0:00")
        self._duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._duration_label.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 13px;"
            f" color: {TEXT_SECONDARY}; background: transparent;"
        )
        self._duration_label.hide()
        layout.addWidget(self._duration_label)

        # Stretch fills remaining space so content stays at top
        layout.addStretch()
        return page

    def _build_file_page(self) -> QWidget:
        """Build the File mode page."""
        page = QWidget()
        page.setObjectName("filePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._drop_zone = DropZoneWidget()
        layout.addWidget(self._drop_zone)
        layout.addSpacing(12)

        self._transcribe_btn = QPushButton(STRINGS["transcribe_btn"])
        self._transcribe_btn.setObjectName("transcribeBtn")
        self._transcribe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._transcribe_btn.setFixedHeight(48)
        self._transcribe_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._transcribe_btn.setEnabled(False)
        layout.addWidget(self._transcribe_btn)
        layout.addStretch()   # push content to top
        return page

    def _build_input_footer(self, layout: QVBoxLayout) -> None:
        """Add the 'Powered by Whisper' footer at the bottom of the input panel."""
        layout.addSpacing(12)
        for text in (STRINGS["powered_by"], STRINGS["runs_local"]):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"font-family: '{FONT_SANS}'; font-size: 11px;"
                f" color: {TEXT_MUTED}; background: transparent;"
            )
            layout.addWidget(lbl)

    def _build_transcript_panel(self) -> QWidget:
        """Construct the right transcript panel."""
        panel = QWidget()
        panel.setObjectName("transcriptPanel")
        panel.setStyleSheet(
            f"QWidget#transcriptPanel {{ background-color: {SURFACE}; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(0)

        section_lbl = QLabel(STRINGS["section_transcript"])
        section_lbl.setStyleSheet(
            f"font-family: '{FONT_SANS}'; font-size: 11px; font-weight: 500;"
            f" letter-spacing: 1px; color: {TEXT_MUTED}; background: transparent;"
        )
        header.addWidget(section_lbl)
        header.addStretch()

        self._word_count_label = QLabel(STRINGS["words_zero"])
        self._word_count_label.setStyleSheet(
            f"font-family: '{FONT_MONO}'; font-size: 11px;"
            f" color: {TEXT_MUTED}; background: transparent;"
        )
        header.addWidget(self._word_count_label)
        layout.addLayout(header)
        layout.addSpacing(12)

        # Transcript text area
        self._transcript = QTextEdit()
        self._transcript.setObjectName("transcriptEdit")
        self._transcript.setReadOnly(True)
        self._transcript.setPlaceholderText(STRINGS["placeholder"])
        self._transcript.setFont(QFont(FONT_SANS, 14))
        self._transcript.viewport().setStyleSheet("background: transparent;")
        layout.addWidget(self._transcript, stretch=1)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addStretch()

        self._copy_btn  = QPushButton(STRINGS["copy_btn"])
        self._save_btn  = QPushButton(STRINGS["save_btn"])
        self._clear_btn = QPushButton(STRINGS["clear_btn"])

        for btn in (self._copy_btn, self._save_btn, self._clear_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            toolbar.addWidget(btn)

        layout.addLayout(toolbar)
        return panel

    def _connect_signals(self) -> None:
        """Wire all button clicks and worker signals."""
        self._mode_toggle.mode_changed.connect(self._on_mode_changed)
        self._record_btn.clicked.connect(self._toggle_recording)
        self._drop_zone.file_selected.connect(self._on_file_selected)
        self._transcribe_btn.clicked.connect(self._start_file_transcription)
        self._copy_btn.clicked.connect(self._copy_transcript)
        self._save_btn.clicked.connect(self._save_transcript)
        self._clear_btn.clicked.connect(self._clear_transcript)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _on_mode_changed(self, index: int) -> None:
        """Switch between Microphone (0) and File (1) pages."""
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Microphone recording
    # ------------------------------------------------------------------

    def _toggle_recording(self) -> None:
        """Start or stop microphone recording."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Create and start the RecorderWorker."""
        self._is_recording = True
        self._chunk_total  = 0
        self._chunks_done  = 0
        self._rec_seconds  = 0

        self._recorder = RecorderWorker(temp_dir=self._temp_dir)
        self._recorder.level.connect(self._level_widget.set_level)
        self._recorder.chunk_ready.connect(self._on_chunk_ready)
        self._recorder.stopped.connect(self._on_recording_stopped)
        self._recorder.error.connect(self._on_worker_error)
        self._recorder.start()

        # Update UI
        self._set_record_button_active(True)
        self._duration_label.setText("0:00")
        self._duration_label.show()
        self._rec_duration_timer.start()
        self._status_bar.set_state("recording")
        logger.info("Recording started")

    def _stop_recording(self) -> None:
        """Signal the recorder to stop."""
        self._is_recording = False
        if self._recorder:
            self._recorder.stop()
        self._record_btn.setEnabled(False)
        self._rec_duration_timer.stop()
        logger.info("Recording stop requested")

    def _on_recording_stopped(self) -> None:
        """Called when RecorderWorker has fully stopped."""
        self._level_widget.reset()
        self._set_record_button_active(False)
        self._record_btn.setEnabled(True)
        if not self._active_workers and not self._pending_chunks:
            self._status_bar.set_state("done")
            self._duration_label.hide()
        logger.info("Recording stopped")

    def _update_rec_duration(self) -> None:
        """Tick the recording duration label every second."""
        self._rec_seconds += 1
        mins  = self._rec_seconds // 60
        secs  = self._rec_seconds % 60
        self._duration_label.setText(f"{mins}:{secs:02d}")

    # ------------------------------------------------------------------
    # Recording → transcription pipeline
    # ------------------------------------------------------------------

    def _on_chunk_ready(self, path: str) -> None:
        """Enqueue a new audio chunk and dispatch a worker if possible."""
        self._chunk_total += 1
        self._pending_chunks.append((path, self._chunk_total))
        self._dispatch_next_chunk()

    def _dispatch_next_chunk(self) -> None:
        """Start transcription for the next queued chunk if a slot is free."""
        while (
            self._pending_chunks
            and len(self._active_workers) < self._MAX_CONCURRENT_WORKERS
        ):
            path, idx = self._pending_chunks.pop(0)
            self._start_transcriber(path, idx, self._chunk_total)

    def _start_transcriber(
        self, audio_path: str, chunk_index: int, chunk_total: int
    ) -> None:
        """Create a TranscriberWorker for one audio chunk / file."""
        model = self._title_bar.model_name()
        worker = TranscriberWorker(
            audio_path=audio_path,
            model_name=model,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
        )
        worker.progress.connect(self._on_transcription_progress)
        worker.status.connect(self._on_transcription_status)
        worker.finished.connect(
            lambda text, w=worker: self._on_transcription_finished(w, text)
        )
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(worker.deleteLater)
        self._active_workers.append(worker)
        worker.start()
        logger.debug("TranscriberWorker started for %s", audio_path)

    def _on_transcription_progress(self, text: str) -> None:
        """Append a transcription segment to the text area."""
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Apply line-height via block format
        fmt = QTextBlockFormat()
        fmt.setLineHeight(160, 1)   # 160% = 1.6 line height
        cursor.setBlockFormat(fmt)

        cursor.insertText(text)
        self._transcript.setTextCursor(cursor)
        self._transcript.ensureCursorVisible()
        self._update_word_count()

    def _on_transcription_status(self, state: str, message: str) -> None:
        """Forward transcriber status to the status bar."""
        self._status_bar.set_state(state, message)

    def _on_transcription_finished(
        self, worker: TranscriberWorker, text: str
    ) -> None:
        """Clean up a finished worker and check if everything is done."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        self._chunks_done += 1

        # Try to dispatch more pending chunks
        self._dispatch_next_chunk()

        # All done?
        if (
            not self._is_recording
            and not self._pending_chunks
            and not self._active_workers
        ):
            self._status_bar.set_state("done")
            self._duration_label.hide()
            self._transcribe_btn.setEnabled(True)
            logger.info("All transcription complete")

    def _on_worker_error(self, message: str) -> None:
        """Display an error in the status bar."""
        logger.error("Worker error: %s", message)
        self._status_bar.set_error(message)
        # Re-enable UI
        self._record_btn.setEnabled(True)
        self._transcribe_btn.setEnabled(bool(self._current_file_path))
        if self._is_recording:
            self._is_recording = False
            self._set_record_button_active(False)
            self._rec_duration_timer.stop()

    # ------------------------------------------------------------------
    # File mode
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: str) -> None:
        """Enable the Transcribe button when a valid file is chosen."""
        self._current_file_path = path
        self._transcribe_btn.setEnabled(True)
        logger.debug("File selected: %s", path)

    def _start_file_transcription(self) -> None:
        """Clear transcript and start transcription for the chosen file."""
        if not self._current_file_path:
            self._status_bar.set_error(STRINGS["err_no_file"])
            return
        self._transcript.clear()
        self._update_word_count()
        self._transcribe_btn.setEnabled(False)
        self._chunk_total = 1
        self._chunks_done = 0
        self._start_transcriber(self._current_file_path, 1, 1)

    # ------------------------------------------------------------------
    # Record button animation helpers
    # ------------------------------------------------------------------

    def _set_record_button_active(self, active: bool) -> None:
        """Toggle the record button between idle (dark) and active (red) states."""
        if active:
            self._record_btn.setObjectName("recordBtnActive")
            self._record_btn.setText(STRINGS["record_active"])
            self._start_pulse()
        else:
            self._record_btn.setObjectName("recordBtnIdle")
            self._record_btn.setText(STRINGS["record_idle"])
            self._stop_pulse()
        self._record_btn.style().unpolish(self._record_btn)
        self._record_btn.style().polish(self._record_btn)

    def _start_pulse(self) -> None:
        """Show and animate the pulsing dot inside the record button."""
        self._pulse_dot.show()
        self._pulse_effect = QGraphicsOpacityEffect(self._pulse_dot)
        self._pulse_dot.setGraphicsEffect(self._pulse_effect)
        self._pulse_anim = QPropertyAnimation(self._pulse_effect, b"opacity")
        self._pulse_anim.setDuration(800)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.3)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._pulse_anim.start()
        # Position dot at left-center of button
        self._pulse_dot.move(14, (self._record_btn.height() - 14) // 2)

    def _stop_pulse(self) -> None:
        """Stop and hide the pulsing dot."""
        if self._pulse_anim:
            self._pulse_anim.stop()
            self._pulse_anim = None
        self._pulse_dot.hide()

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _copy_transcript(self) -> None:
        """Copy transcript to clipboard and briefly flash 'Copied ✓'."""
        text = self._transcript.toPlainText().strip()
        if not text:
            self._status_bar.set_error(STRINGS["err_empty_copy"])
            return
        QApplication.clipboard().setText(text)
        self._copy_btn.setText(STRINGS["copy_done"])
        self._copy_btn.setStyleSheet(f"color: {GREEN};")
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        """Revert copy button to its default label and style."""
        self._copy_btn.setText(STRINGS["copy_btn"])
        self._copy_btn.setStyleSheet("")

    def _save_transcript(self) -> None:
        """Open a save dialog and write the transcript to a .txt file."""
        text = self._transcript.toPlainText().strip()
        if not text:
            self._status_bar.set_error(STRINGS["err_empty_save"])
            return
        default_name = (
            "transcript_"
            + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            + ".txt"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Transcript", default_name, "Text files (*.txt)"
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                short = Path(path).name
                self._status_bar.set_state(
                    "done", STRINGS["saved_msg"] + short
                )
                logger.info("Transcript saved to %s", path)
            except OSError as exc:
                self._status_bar.set_error(str(exc))
                logger.error("Save failed: %s", exc)

    def _clear_transcript(self) -> None:
        """Ask for confirmation then clear the transcript."""
        box = QMessageBox(self)
        box.setWindowTitle(STRINGS["clear_title"])
        box.setText(STRINGS["clear_body"])
        box.setIcon(QMessageBox.Icon.Question)
        confirm_btn = box.addButton(
            STRINGS["clear_confirm"], QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(
            STRINGS["clear_cancel"], QMessageBox.ButtonRole.RejectRole
        )
        box.setDefaultButton(confirm_btn)
        box.exec()
        if box.clickedButton() is confirm_btn:
            self._transcript.clear()
            self._update_word_count()
            self._status_bar.set_state("idle")
            logger.debug("Transcript cleared by user")

    # ------------------------------------------------------------------
    # Word count
    # ------------------------------------------------------------------

    def _update_word_count(self) -> None:
        """Recount words in the transcript and update the label."""
        text  = self._transcript.toPlainText().strip()
        count = len(text.split()) if text else 0
        label = f"{count} word{'s' if count != 1 else ''}"
        self._word_count_label.setText(label)

    # ------------------------------------------------------------------
    # Window resize handle (bottom-right corner drag)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle resize initiation from the window border area."""
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Draw a subtle border around the frameless window."""
        painter = QPainter(self)
        painter.setPen(QColor(BORDER_STRONG))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()
