#!/usr/bin/env python3
"""
Build script for FFmpeg Converter - Cross-platform (Windows, Linux, macOS)
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def run_command(cmd: list[str], cwd: str = None):
    """Execute command and print output."""
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise Exception(f"Command returned code {result.returncode}")
    return result


def get_hidden_imports() -> list[str]:
    """Get common hidden imports for all platforms."""
    return [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'src.core.ffmpeg',
        'src.core.presets',
        'src.core.ffmpeg_installer',
        'src.core.ffmpeg_updater',
        'src.platforms',
        'src.i18n',
        'src.i18n.translator',
        'src.i18n.locale',
        'urllib.request',
        'zipfile',
        'json',
    ]


def get_icon_path() -> str:
    """Get icon path for current platform."""
    system = platform.system()
    if system == 'Darwin':
        return 'assets/icons/icon.icns'
    elif system == 'Windows':
        return 'assets/icons/icon.ico'
    else:
        return 'assets/icons/icon.png'


def generate_spec_windows() -> str:
    """Generate PyInstaller spec for Windows."""
    icon = get_icon_path()
    hidden = "',\n        '".join(get_hidden_imports())
    
    return f"""# -*- mode: python ; coding: utf-8 -*-
# Windows ONE FILE BUILD

block_cipher = None

a = Analysis(
    ['src/main_pyqt.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons', 'assets/icons'),
        ('version.txt', '.'),
        ('translations/ru.qm', 'translations'),
        ('translations/en.qm', 'translations'),
    ],
    hiddenimports=[
        '{hidden}',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFmpegConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon}',
    version='version.txt',
    onefile=True,
)
"""


def generate_spec_linux() -> str:
    """Generate PyInstaller spec for Linux."""
    icon = get_icon_path()
    hidden = "',\n        '".join(get_hidden_imports())
    
    return f"""# -*- mode: python ; coding: utf-8 -*-
# Linux ONE FILE BUILD

block_cipher = None

a = Analysis(
    ['src/main_pyqt.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons', 'assets/icons'),
        ('translations/ru.qm', 'translations'),
        ('translations/en.qm', 'translations'),
    ],
    hiddenimports=[
        '{hidden}',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFmpegConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon}',
    onefile=True,
)
"""


def generate_spec_macos() -> str:
    """Generate PyInstaller spec for macOS (.app bundle)."""
    icon = get_icon_path()
    hidden = "',\n        '".join(get_hidden_imports())
    
    return f"""# -*- mode: python ; coding: utf-8 -*-
# macOS .app BUNDLE BUILD

block_cipher = None

a = Analysis(
    ['src/main_pyqt.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons', 'assets/icons'),
        ('translations/ru.qm', 'translations'),
        ('translations/en.qm', 'translations'),
    ],
    hiddenimports=[
        '{hidden}',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = BUNDLE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFmpegConverter.app',
    icon='{icon}',
    bundle_identifier='com.aagarin39.ffmpegconverter',
    info_plist={{
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '11.0',
    }},
)
"""


def build_windows():
    """Build for Windows (.exe) - ONE FILE."""
    print("\n=== Building for Windows ===")
    
    spec_content = generate_spec_windows()
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n[OK] Windows build complete!")
    print(f"  File: dist/FFmpegConverter.exe")
    print(f"  Size: ~43 MB")
    print(f"\n  User gets ONE file!")
    print(f"  To uninstall - just delete .exe")


def build_linux():
    """Build for Linux - ONE FILE binary + .desktop file."""
    print("\n=== Building for Linux ===")
    
    spec_content = generate_spec_linux()
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    desktop_content = """[Desktop Entry]
Name=FFmpeg Converter
Comment=Video and image converter with FFmpeg
Exec=FFmpegConverter
Icon=ffmpegconverter
Terminal=false
Type=Application
Categories=AudioVideo;Video;Graphics;
Keywords=video;convert;ffmpeg;
"""
    
    Path('dist/FFmpegConverter.desktop').write_text(desktop_content, encoding='utf-8')
    
    if Path('assets/icons/icon.png').exists():
        shutil.copy2('assets/icons/icon.png', 'dist/ffmpegconverter.png')
    
    print("\n[OK] Linux build complete!")
    print(f"  Binary: dist/FFmpegConverter")
    print(f"  Desktop: dist/FFmpegConverter.desktop")
    print(f"  Icon: dist/ffmpegconverter.png")
    print(f"\n  Installation:")
    print(f"    cp dist/FFmpegConverter /usr/local/bin/")
    print(f"    cp dist/FFmpegConverter.desktop ~/.local/share/applications/")
    print(f"    cp dist/ffmpegconverter.png ~/.local/share/icons/")


def build_macos():
    """Build for macOS - .app bundle."""
    print("\n=== Building for macOS ===")
    
    if not Path('assets/icons/icon.icns').exists():
        print("WARNING: icon.icns not found, using default icon")
    
    spec_content = generate_spec_macos()
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n[OK] macOS build complete!")
    print(f"  App: dist/FFmpegConverter.app")
    print(f"\n  Usage:")
    print(f"    Open dist/FFmpegConverter.app")
    print(f"    Or: open dist/FFmpegConverter.app")
    print(f"\n  Note: If Gatekeeper blocks the app, run:")
    print(f"    xattr -dr com.apple.quarantine dist/FFmpegConverter.app")


def create_readme_dist():
    """Create README for distribution."""
    system = platform.system()
    
    if system == 'Windows':
        readme = """================================================================================
                          FFmpeg Converter v0.4.0
================================================================================

Installation and Usage
----------------------

1. Install FFmpeg (first run):
   - Run FFmpegConverter.exe
   - Click "Install FFmpeg"
   - Wait for completion (~30-60 seconds)

2. Usage:
   - Select folder with video/photo
   - Select preset
   - Click "Convert"

Uninstall FFmpeg (~580 MB)
--------------------------

Desktop shortcut:
   - "Uninstall FFmpeg.lnk" -> double click

Or in program:
   - Click status "FFmpeg X.X"
   - "Uninstall FFmpeg"

Files in distribution
---------------------

- FFmpegConverter.exe (43 MB) - Program

Data: %USERPROFILE%/FFmpegGUI/

Repository: https://github.com/aagarin39/FFmpegGUI.git
License: MIT
================================================================================
"""
    elif system == 'Linux':
        readme = """================================================================================
                          FFmpeg Converter v0.4.0
================================================================================

Installation
------------

1. Copy binary:
   sudo cp FFmpegConverter /usr/local/bin/

2. Copy desktop entry:
   cp FFmpegConverter.desktop ~/.local/share/applications/

3. Copy icon:
   cp ffmpegconverter.png ~/.local/share/icons/

4. Install FFmpeg:
   sudo apt install ffmpeg        # Debian/Ubuntu
   sudo dnf install ffmpeg        # Fedora
   sudo pacman -S ffmpeg          # Arch

Usage
-----

- Run: FFmpegConverter
- Or find "FFmpeg Converter" in application menu

Data: ~/.config/FFmpegGUI/

Repository: https://github.com/aagarin39/FFmpegGUI.git
License: MIT
================================================================================
"""
    else:
        readme = """================================================================================
                          FFmpeg Converter v0.4.0
================================================================================

Installation
------------

1. Install FFmpeg:
   brew install ffmpeg

2. Run the app:
   open FFmpegConverter.app

3. If Gatekeeper blocks:
   xattr -dr com.apple.quarantine FFmpegConverter.app

Usage
-----

- Double-click FFmpegConverter.app
- Or drag to Applications folder

Data: ~/Library/Application Support/FFmpegGUI/

Repository: https://github.com/aagarin39/FFmpegGUI.git
License: MIT
================================================================================
"""
    
    Path('dist/README.txt').write_text(readme, encoding='utf-8')


def main():
    system = platform.system()
    
    print(f"Building FFmpegGUI for {system}")
    print("=" * 50)
    
    Path('dist').mkdir(exist_ok=True)
    
    if system == 'Windows':
        build_windows()
    elif system == 'Linux':
        build_linux()
    elif system == 'Darwin':
        build_macos()
    else:
        print(f"Unsupported OS: {system}")
        sys.exit(1)
    
    create_readme_dist()
    
    print("\n" + "=" * 50)
    print("[OK] Build complete!")
    print(f"  Distribution in: dist/")


if __name__ == '__main__':
    main()
