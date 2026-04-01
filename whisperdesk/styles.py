"""
styles.py — Visual design tokens and QSS stylesheet for WhisperDesk.

Defines all color constants, font names, and the full Qt Style Sheet string
that is applied to the QApplication at startup.
"""

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BG            = "#FAFAF8"   # App background (warm off-white)
SURFACE       = "#FFFFFF"   # Panel / card surfaces
BORDER        = "#E8E6E0"   # Default border color
BORDER_STRONG = "#D0CEC8"   # Stronger border (hover states, inputs)
TEXT_PRIMARY  = "#1A1A18"   # Primary text (near-black, warm tint)
TEXT_SECONDARY = "#6B6860"  # Secondary text (medium gray-brown)
TEXT_MUTED    = "#9E9C96"   # Muted / placeholder text
ACCENT        = "#1A1A18"   # Same as TEXT_PRIMARY — primary button fill
ACCENT_HOVER  = "#3A3A36"   # Slightly lighter for button hover
GREEN         = "#2D6A4F"   # Status green (success / active)
GREEN_BG      = "#EAF3EE"   # Green badge background
GREEN_BORDER  = "#B7D9C7"   # Green badge border
RED_RECORD    = "#FF3B30"   # Record button active color
RED_HOVER     = "#E0352A"   # Record button hover while recording
MUTED_BG      = "#F2F0EB"   # Title bar background

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_SANS = "Segoe UI"    # System font, always available on Windows
FONT_MONO = "Consolas"    # Monospace font, always available on Windows

# ---------------------------------------------------------------------------
# Application version
# ---------------------------------------------------------------------------
APP_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Full QSS stylesheet — applied once to QApplication
# ---------------------------------------------------------------------------
APP_STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QWidget {{
    font-family: "{FONT_SANS}";
    font-size: 14px;
    color: {TEXT_PRIMARY};
    background-color: {BG};
}}

/* ── Main window & central widget ────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {BG};
}}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
}}
QSplitter::handle:hover {{
    background-color: {BORDER_STRONG};
}}

/* ── QFrame generic ──────────────────────────────────────────────────────── */
QFrame {{
    background-color: transparent;
    border: none;
}}

/* ── QLabel ──────────────────────────────────────────────────────────────── */
QLabel {{
    background-color: transparent;
    border: none;
}}

/* ── QPushButton — default toolbar/action style ─────────────────────────── */
QPushButton {{
    font-family: "{FONT_SANS}";
    font-size: 13px;
    color: {TEXT_SECONDARY};
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 7px;
    padding: 0px 14px;
    height: 32px;
}}
QPushButton:hover {{
    border-color: {TEXT_PRIMARY};
    color: {TEXT_PRIMARY};
}}
QPushButton:pressed {{
    background-color: {MUTED_BG};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
    background-color: {SURFACE};
    opacity: 0.4;
}}

/* ── Record button — idle (dark) ─────────────────────────────────────────── */
QPushButton#recordBtnIdle {{
    font-family: "{FONT_SANS}";
    font-size: 14px;
    font-weight: 500;
    color: {BG};
    background-color: {ACCENT};
    border: none;
    border-radius: 10px;
    height: 48px;
    padding: 0px 16px;
}}
QPushButton#recordBtnIdle:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#recordBtnIdle:pressed {{
    background-color: {TEXT_PRIMARY};
}}
QPushButton#recordBtnIdle:disabled {{
    background-color: {TEXT_MUTED};
    color: {SURFACE};
}}

/* ── Record button — active (red) ────────────────────────────────────────── */
QPushButton#recordBtnActive {{
    font-family: "{FONT_SANS}";
    font-size: 14px;
    font-weight: 500;
    color: #FFFFFF;
    background-color: {RED_RECORD};
    border: none;
    border-radius: 10px;
    height: 48px;
    padding: 0px 16px;
}}
QPushButton#recordBtnActive:hover {{
    background-color: {RED_HOVER};
}}
QPushButton#recordBtnActive:pressed {{
    background-color: #CC2E25;
}}

/* ── Transcribe file button ──────────────────────────────────────────────── */
QPushButton#transcribeBtn {{
    font-family: "{FONT_SANS}";
    font-size: 14px;
    font-weight: 500;
    color: {BG};
    background-color: {ACCENT};
    border: none;
    border-radius: 10px;
    height: 48px;
    padding: 0px 16px;
}}
QPushButton#transcribeBtn:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#transcribeBtn:pressed {{
    background-color: {TEXT_PRIMARY};
}}
QPushButton#transcribeBtn:disabled {{
    background-color: {TEXT_MUTED};
    color: {SURFACE};
}}

/* ── Mode toggle buttons ─────────────────────────────────────────────────── */
QPushButton#modeBtn {{
    font-family: "{FONT_SANS}";
    font-size: 13px;
    color: {TEXT_SECONDARY};
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 0px;
    height: 28px;
}}
QPushButton#modeBtnActive {{
    font-family: "{FONT_SANS}";
    font-size: 13px;
    font-weight: 500;
    color: {TEXT_PRIMARY};
    background-color: {SURFACE};
    border: none;
    border-radius: 6px;
    padding: 6px 0px;
    height: 28px;
}}

/* ── QComboBox — model selector ──────────────────────────────────────────── */
QComboBox#modelSelector {{
    font-family: "{FONT_SANS}";
    font-size: 12px;
    color: {TEXT_PRIMARY};
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 4px 8px;
    min-width: 90px;
}}
QComboBox#modelSelector:hover {{
    border-color: {TEXT_PRIMARY};
}}
QComboBox#modelSelector::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox#modelSelector::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    selection-background-color: {MUTED_BG};
    selection-color: {TEXT_PRIMARY};
    font-family: "{FONT_SANS}";
    font-size: 12px;
    padding: 2px;
}}

/* ── QTextEdit — transcript area ─────────────────────────────────────────── */
QTextEdit#transcriptEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px;
    font-family: "{FONT_SANS}";
    font-size: 14px;
    color: {TEXT_PRIMARY};
    selection-background-color: {MUTED_BG};
}}
QTextEdit#transcriptEdit:focus {{
    border-color: {BORDER_STRONG};
    outline: none;
}}

/* ── Scrollbars — thin and minimal ──────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── Drop zone frame ─────────────────────────────────────────────────────── */
QFrame#dropZone {{
    background-color: {SURFACE};
    border: 2px dashed {BORDER_STRONG};
    border-radius: 10px;
}}
QFrame#dropZoneHover {{
    background-color: {BG};
    border: 2px dashed {TEXT_PRIMARY};
    border-radius: 10px;
}}
QFrame#dropZoneDrag {{
    background-color: {MUTED_BG};
    border: 2px solid {TEXT_PRIMARY};
    border-radius: 10px;
}}
QFrame#dropZoneAccepted {{
    background-color: {GREEN_BG};
    border: 1px solid {GREEN_BORDER};
    border-radius: 10px;
}}
QFrame#dropZoneRejected {{
    background-color: #FFF0F0;
    border: 2px dashed #FFCCCC;
    border-radius: 10px;
}}

/* ── Status bar frame ────────────────────────────────────────────────────── */
QFrame#statusBar {{
    background-color: {BG};
    border-top: 1px solid {BORDER};
}}

/* ── Title bar frame ─────────────────────────────────────────────────────── */
QFrame#titleBar {{
    background-color: {MUTED_BG};
    border-bottom: 1px solid {BORDER};
}}

/* ── QToolTip ────────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {TEXT_PRIMARY};
    color: #FFFFFF;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-family: "{FONT_SANS}";
    font-size: 12px;
}}

/* ── QMessageBox ─────────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {SURFACE};
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    min-width: 80px;
    height: 30px;
}}

/* ── Stacked page backgrounds ────────────────────────────────────────────── */
QWidget#micPage, QWidget#filePage {{
    background-color: transparent;
}}

/* ── QScrollArea ─────────────────────────────────────────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}
"""
