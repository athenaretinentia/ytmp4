#!/usr/bin/env python3
"""
Build macOS .app bundle for ytmp4 Converter with custom icon.
Run: python3 build_app.py
"""

import os, shutil, subprocess, glob

DESKTOP  = os.path.expanduser("~/Desktop")
APP_NAME = "ytmp4 Converter"
APP_PATH = os.path.join(DESKTOP, f"{APP_NAME}.app")
ICON_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
GUI_SRC  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ytmp4_converter.py")

def q(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def create_icns():
    """Create .icns from icon.png using macOS built-in tools."""
    work = "/tmp/ytmp4_iconwork"
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)

    # Convert PNG to PNG (re-encode as sips can be picky)
    base = os.path.join(work, "base.png")
    q(["sips", "-s", "format", "png", ICON_SRC, "--out", base], timeout=30)

    sizes = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
    ]

    for name, sz in sizes:
        out = os.path.join(work, name)
        q(["sips", "-z", str(sz), str(sz), base, "--out", out], timeout=30)

    iconset = "/tmp/ytmp4.iconset"
    if os.path.exists(iconset):
        shutil.rmtree(iconset)
    os.rename(work, iconset)

    icns_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppIcon.icns")
    r = q(["iconutil", "-c", "icns", iconset, "-o", icns_out], timeout=30)
    shutil.rmtree(iconset, ignore_errors=True)

    if r.returncode == 0 and os.path.exists(icns_out):
        return icns_out
    return None


def main():
    print(f"Building {APP_NAME}.app...")

    if not os.path.exists(ICON_SRC):
        print(f"Error: {ICON_SRC} not found.")
        return

    # Create .icns
    icns = create_icns()
    if not icns:
        print("Warning: Could not create .icns, app will have no icon.")
        icns = None

    # Remove old app
    if os.path.exists(APP_PATH):
        shutil.rmtree(APP_PATH)

    # Create bundle structure
    resources = os.path.join(APP_PATH, "Contents", "Resources")
    macos_dir = os.path.join(APP_PATH, "Contents", "MacOS")
    os.makedirs(resources, exist_ok=True)
    os.makedirs(macos_dir, exist_ok=True)

    # Copy icon
    if icns and os.path.exists(icns):
        shutil.copy(icns, os.path.join(resources, "AppIcon.icns"))

    # Copy GUI script into the app bundle
    shutil.copy(GUI_SRC, os.path.join(resources, "ytmp4_converter.py"))

    # Launcher script
    launcher = os.path.join(macos_dir, APP_NAME)
    with open(launcher, "w") as f:
        f.write('''#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
cd "$HOME"
DIR="$(dirname "$0")/../Resources"
PYTHON=""
for p in /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    [ -x "$p" ] && PYTHON="$p" && break
done
if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "Python 3 is required.\\nInstall from python.org" buttons "OK" default button 1'
    exit 1
fi
"$PYTHON" "$DIR/ytmp4_converter.py"
''')
    os.chmod(launcher, 0o755)

    # Info.plist
    plist_path = os.path.join(APP_PATH, "Contents", "Info.plist")
    with open(plist_path, "w") as f:
        f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>''' + APP_NAME + '''</string>
    <key>CFBundleIdentifier</key>
    <string>com.ytmp4.converter</string>
    <key>CFBundleName</key>
    <string>''' + APP_NAME + '''</string>
    <key>CFBundleDisplayName</key>
    <string>''' + APP_NAME + '''</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
''')

    size = sum(os.path.getsize(os.path.join(dirpath, f))
               for dirpath, _, filenames in os.walk(APP_PATH)
               for f in filenames)
    print(f"Done! {APP_PATH} ({size / 1024:.0f} KB)")
    print(f"Double-click {APP_NAME}.app on your Desktop to launch.")


if __name__ == "__main__":
    main()
