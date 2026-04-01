"""
main.py — Entry point for WhisperDesk.

Creates the QApplication, applies the stylesheet, ensures the temp directory
exists, and launches the main window.
"""

import sys
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from styles import APP_STYLESHEET
from ui import MainWindow


def _configure_logging() -> None:
    """Set up logging to both file and stderr at DEBUG level."""
    log_path = Path(__file__).parent / "whisperdesk.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _ensure_temp_dir() -> Path:
    """Create the temp/ directory next to main.py and return its path."""
    temp = Path(__file__).parent / "temp"
    temp.mkdir(exist_ok=True)
    return temp


def main() -> None:
    """Bootstrap the application."""
    _configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("WhisperDesk starting up")

    temp_dir = _ensure_temp_dir()
    logger.debug("Temp directory: %s", temp_dir)

    app = QApplication(sys.argv)
    app.setApplicationName("WhisperDesk")
    app.setApplicationVersion("1.0.0")

    # Fusion style gives QSS the most control on Windows
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow(temp_dir=str(temp_dir))
    window.show()

    logger.info("Event loop started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
