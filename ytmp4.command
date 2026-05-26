#!/bin/bash
# ytmp4 — YouTube to MP4 Converter (macOS Launcher)
# Double-click this file to launch the GUI.

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# Auto-detect Python3
PYTHON=""
for p in /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    [ -x "$p" ] && PYTHON="$p" && break
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3 not found. Install Python 3 from python.org"
    exit 1
fi

cd "$HOME"
"$PYTHON" "$HOME/Desktop/ytmp4_converter.py"
