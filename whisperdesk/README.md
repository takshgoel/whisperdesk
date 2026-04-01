# WhisperDesk

## What is WhisperDesk?

WhisperDesk is a free, local speech-to-text app for Windows. It transcribes your microphone or audio files entirely on your own PC — no internet connection or API key required after the first model download.

---

## What you need before installing

- **Windows 10 or 11 (64-bit)**
- **Python 3.10 or newer** — https://python.org
- **ffmpeg for Windows** — required to convert MP3/M4A/OGG files to WAV before transcription
  1. Download the latest "essentials" build from https://www.gyan.dev/ffmpeg/builds/
  2. Extract the zip to a folder such as `C:\ffmpeg`
  3. Add `C:\ffmpeg\bin` to your Windows PATH:
     - Open **Settings → System → About → Advanced system settings**
     - Click **Environment Variables**
     - Under *System variables* select **Path** and click **Edit**
     - Click **New** and enter `C:\ffmpeg\bin`
     - Click OK on all dialogs and restart any open terminals
  4. Verify: open a new terminal and type `ffmpeg -version`
- **~500 MB free disk space** (for the Whisper "base" model and app dependencies)

---

## Installation

```
git clone https://github.com/yourusername/whisperdesk.git
cd whisperdesk
pip install -r requirements.txt
```

> **Tip — CPU-only torch (faster install, smaller download):**
> ```
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

---

## How to run

```
python main.py
```

> **First launch note:** The first time you run WhisperDesk it downloads the Whisper "base" model (~140 MB). This happens once and is stored in your user cache. Subsequent launches are instant.

---

## Using Mic Mode

1. Make sure the **Microphone** tab is selected in the left panel.
2. Click **Start Recording**.
3. Speak naturally — transcription begins automatically every 8 seconds.
4. Click **Stop Recording** when finished.
5. The transcript appears in the right panel.
6. Click **Copy** to copy to clipboard, or **Save .txt** to save a text file.

---

## Using File Mode

1. Click the **File** tab in the left panel.
2. Drag an audio file onto the drop zone, or click the zone to open a file browser.
   - Supported formats: **MP3, WAV, M4A, OGG, FLAC**
3. Click **Transcribe File**.
4. Wait for processing (progress is shown in the status bar at the bottom).
5. The transcript appears in the right panel.
6. Click **Copy** or **Save .txt**.

---

## Changing transcription quality

Use the **Model** dropdown in the top-right corner of the title bar:

| Model  | Speed    | Accuracy | RAM usage |
|--------|----------|----------|-----------|
| tiny   | Fastest  | Good     | ~1 GB     |
| base   | Fast     | Better   | ~1 GB     |
| small  | Moderate | Best     | ~2 GB     |

"base" is the default and works well for most English speech.
Switch to "small" for accented speech or technical content.
Use "tiny" on slower machines or when speed matters most.

---

## Troubleshooting

**1. `ffmpeg not found` error**
ffmpeg is not on your Windows PATH.
Fix: follow the ffmpeg installation steps above, then close and reopen your terminal.

**2. `No module named 'sounddevice'`**
Run: `pip install sounddevice`

**3. App freezes during transcription**
This should not happen — transcription runs on a background thread.
If it does, close and restart the app.  Large files on slow machines may take a minute before the first segment appears.

**4. Microphone not working / no audio level**
Check **Windows Settings → Privacy & security → Microphone** and ensure Python is allowed microphone access.
Also check that your microphone is set as the default recording device in **Sound settings**.

**5. `torch` install fails or is very slow**
Install the CPU-only version of PyTorch first, then install the rest:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```
