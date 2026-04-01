# -*- mode: python ; coding: utf-8 -*-
#
# whisperdesk.spec — PyInstaller build specification for WhisperDesk.
#
# Run with:   pyinstaller whisperdesk.spec
#
# The output is placed in dist\WhisperDesk\.
# The folder can be zipped and distributed as-is, or fed into Inno Setup
# to produce a single-file installer.
#
# NOTE: First run may take 10-20 minutes because PyInstaller has to scan
# the entire torch package (~1 GB of files).

import sys
import os
from pathlib import Path
import PyQt6
import whisper as _whisper
import torch as _torch

# ── Locate key package directories ──────────────────────────────────────────
SITE_PACKAGES = Path(sys.executable).parent / "Lib" / "site-packages"
WHISPER_DIR   = Path(_whisper.__file__).parent
TORCH_DIR     = Path(_torch.__file__).parent
PYQT6_DIR     = Path(PyQt6.__file__).parent

block_cipher = None

# ── Data files to bundle ────────────────────────────────────────────────────
# Format: (source_path_or_glob, dest_folder_inside_bundle)
added_datas = [
    # Whisper tokenizer assets (mel filters, tiktoken BPE files)
    (str(WHISPER_DIR / "assets"),          "whisper/assets"),
    # Whisper normaliser JSON
    (str(WHISPER_DIR / "normalizers"),     "whisper/normalizers"),
    # PyQt6 Qt platform plugins (needed for windowed mode on Windows)
    (str(PYQT6_DIR / "Qt6" / "plugins"),  "PyQt6/Qt6/plugins"),
    # PyQt6 Qt libraries
    (str(PYQT6_DIR / "Qt6" / "bin"),      "PyQt6/Qt6/bin"),
]

# ── Hidden imports PyInstaller misses via static analysis ───────────────────
hidden_imports = [
    # Whisper
    "whisper",
    "whisper.audio",
    "whisper.decoding",
    "whisper.model",
    "whisper.normalizers",
    "whisper.timing",
    "whisper.tokenizer",
    "whisper.transcribe",
    "whisper.utils",
    # tiktoken (whisper tokeniser)
    "tiktoken",
    "tiktoken.core",
    "tiktoken.registry",
    "tiktoken.load",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    # torch & friends
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "torch.jit",
    # numba / llvmlite (pulled in by whisper on some builds)
    "numba",
    "numba.core",
    "llvmlite",
    # Audio
    "sounddevice",
    "soundfile",
    "scipy",
    "scipy.signal",
    "scipy.io",
    "scipy.io.wavfile",
    # PyQt6
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",
    # numpy
    "numpy",
    "numpy.core",
    "numpy.fft",
    "numpy.random",
]

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy packages we don't use to keep bundle smaller
    excludes=[
        "matplotlib",
        "PIL",
        "Pillow",
        "IPython",
        "jupyter",
        "notebook",
        "pandas",
        "sklearn",
        "cv2",
        "tensorflow",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WhisperDesk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,             # compress with UPX if available (smaller output)
    console=False,        # no black console window (windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # uncomment after adding an .ico file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WhisperDesk",   # output folder: dist\WhisperDesk\
)
