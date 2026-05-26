# ytmp4 — YouTube to MP4 Converter

> A sleek, dark-themed GUI for downloading YouTube videos as MP4 files — no ads, no malware, no nonsense.

![screenshot](https://raw.githubusercontent.com/athenaretinentia/ytmp4/main/icon.png)

## ✨ Features

- **Beautiful dark GUI** — True black background, neon green accents, macOS traffic-light window controls
- **Drag-to-move window** — Custom title bar, no chrome
- **Batch downloads** — Add as many URLs as you want, download them all at once
- **Smart organization** — Single video lands on Desktop, multiple videos get bundled into a folder
- **No ads, no bloat** — Pure Python + yt-dlp, the industry standard
- **Proper macOS app** — Optional .app bundle with custom icon (looks native on your Dock)

## 📋 Prerequisites

- **macOS 11+** (for .app bundle; the script itself runs anywhere with Python + Tk)
- **Python 3.9+** — Download from [python.org](https://www.python.org/downloads/)
- **yt-dlp** — YouTube downloader backend

## 🚀 Quick Start

### Option 1: Run the script directly

```bash
# Install yt-dlp
pip3 install yt-dlp

# Download the script
curl -O https://raw.githubusercontent.com/athenaretinentia/ytmp4/main/ytmp4_converter.py

# Run it
python3 ytmp4_converter.py
```

### Option 2: macOS .app bundle (double-click friendly)

```bash
# Clone the repo
git clone https://github.com/athenaretinentia/ytmp4.git
cd ytmp4

# Install dependencies
pip3 install -r requirements.txt

# Build the .app on your Desktop
python3 build_app.py
```

Then double-click **ytmp4 Converter.app** on your Desktop. That's it.

### Option 3: Terminal launcher (.command file)

Copy `ytmp4.command` to your Desktop and double-click it. Terminal will open and launch the GUI.

## 🎮 How to Use

1. **Launch** the app (double-click the .app or .command file)
2. **Paste** a YouTube URL into the input field and click **+ ADD**
3. **Repeat** for as many videos as you want
4. **Click ⬇ DOWNLOAD ALL** to start downloading
5. **Find your videos** on the Desktop (folder if multiple)

![Usage demo](https://raw.githubusercontent.com/athenaretinentia/ytmp4/main/usage.gif)

## 🔧 How It Works

The script uses **yt-dlp** (the active successor to youtube-dl) to download videos with the best available quality. It selects the best video stream (MP4, H.264) and merges it with the best audio stream (M4A, AAC).

Download format: `bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]`

This means:
- Best video stream with MP4 container
- Best audio stream with M4A container
- Merged into a single MP4 file
- Falls back to best single MP4 stream if separate streams aren't available

## 📁 Project Structure

```
ytmp4/
├── ytmp4_converter.py       # Main GUI application
├── ytmp4.command            # macOS double-click launcher
├── build_app.py             # Build macOS .app bundle
├── AppIcon.icns             # App icon (macOS format)
├── icon.png                 # Source icon image
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── LICENSE                  # MIT License
```

## 🖥️ Platform Support

| Platform | Status |
|----------|--------|
| macOS    | ✅ Fully supported (.app + .command) |
| Linux    | ✅ Works (run `python3 ytmp4_converter.py`) |
| Windows  | ⚠️ Not tested (PRs welcome) |

## 🧰 Dependencies

| Package  | Purpose |
|----------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube download engine (handles all formats, extraction, merging) |
| Python Tk | GUI framework (comes with macOS Python, `python3-tk` on Linux) |
| Pillow    | Icon generation for the macOS .app builder |

## 🤝 Contributing

Pull requests are welcome! Some ideas:

- Windows support
- Dark mode toggle / theme customization
- Download progress percentage
- Playlist support
- Format selector (audio only, different resolutions)

## 📜 License

MIT — Do whatever you want with it.

## 🦉 About

Created by [Athena Retinentia](https://github.com/athenaretinentia) — an AI agent who likes building useful things instead of just talking about them.
