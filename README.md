# WhisperDesk 🎙️

> **Local, offline speech-to-text for Windows. No API key. No cloud. No cost.**

WhisperDesk transcribes your microphone or audio files entirely on your own PC using [OpenAI Whisper](https://github.com/openai/whisper). Once the model is downloaded (once, ~140 MB) it works 100% offline — your voice never leaves your machine.

---

## Download

| Platform | Link |
|---|---|
| Windows 10 / 11 (64-bit) | [**WhisperDesk_Setup_v1.0.0.exe**](../../releases/latest) |

> The installer is ~800 MB — it bundles Python, PyTorch, and everything needed. No separate installs required.

---

## Screenshots

<!-- Add screenshots here after building -->
*Coming soon*

---

## Features

- 🎤 **Live mic transcription** — records in 8-second chunks, transcribes continuously
- 📁 **Audio file support** — drag and drop MP3, WAV, M4A, OGG, FLAC
- 🔒 **100% offline** — after first model download, no internet needed
- ⚡ **Three model sizes** — Tiny (fastest) · Base (balanced) · Small (most accurate)
- 📋 **One-click export** — copy to clipboard or save as .txt
- 🪶 **Lightweight UI** — clean minimal design, never freezes during transcription

---

## Run from source

Prefer to run the Python source directly? You'll need:

- **Windows 10 or 11 (64-bit)**
- **Python 3.10+** — https://python.org
- **ffmpeg** (for MP3/M4A/OGG files only) — https://www.gyan.dev/ffmpeg/builds/
  - Extract to `C:\ffmpeg`, add `C:\ffmpeg\bin` to your PATH

```bash
git clone https://github.com/yourusername/whisperdesk.git
cd whisperdesk/whisperdesk

# Install CPU-only PyTorch first (faster, smaller)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install everything else
pip install -r requirements.txt

# Run
python main.py
```

First launch downloads the Whisper "base" model (~140 MB, one time only).

---

## Usage

### Microphone
1. Select the **Microphone** tab
2. Click **Start Recording** — the button turns red, audio level bar activates
3. Speak — transcript appears automatically every 8 seconds
4. Click **Stop Recording**
5. Click **Copy** or **Save .txt**

### Audio File
1. Select the **File** tab
2. Drag an audio file onto the drop zone, or click to browse
3. Click **Transcribe File**
4. Wait for processing (status bar shows progress)
5. Click **Copy** or **Save .txt**

### Model selector
Top-right corner of the app:

| Model | Speed | Best for |
|---|---|---|
| tiny | Fastest | Quick notes, fast machines |
| base | Balanced *(default)* | Most everyday use |
| small | Slower, more accurate | Accented speech, technical content |

---

## Building from source (for distributors)

```bash
cd whisperdesk
pip install pyinstaller
build.bat
```

Then open `installer.iss` in [Inno Setup](https://jrsoftware.org/isdl.php) and press **Ctrl+F9** to compile the installer.

See [BUILDING.md](whisperdesk/BUILDING.md) for full details.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | Add `C:\ffmpeg\bin` to Windows PATH, restart terminal |
| No microphone level | Check **Settings → Privacy → Microphone**, allow Python |
| Slow first transcription | Normal — model loads into RAM once, fast after |
| `torch` install fails | `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| App crashes on launch | Check `whisperdesk\whisperdesk.log` for details |

---

## Tech stack

| Component | Library |
|---|---|
| GUI | [PyQt6](https://pypi.org/project/PyQt6/) |
| Transcription | [openai-whisper](https://github.com/openai/whisper) |
| Mic capture | [sounddevice](https://pypi.org/project/sounddevice/) |
| Audio I/O | [soundfile](https://pypi.org/project/SoundFile/) |
| Audio conversion | [ffmpeg](https://ffmpeg.org/) |
| ML backend | [PyTorch](https://pytorch.org/) (CPU) |

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

*Powered by [OpenAI Whisper](https://github.com/openai/whisper)*
