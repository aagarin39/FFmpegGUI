#!/usr/bin/env python3
"""
Build script for FFmpeg Converter - ONE FILE for user
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


def build_windows():
    """Build for Windows (.exe) - ONE FILE."""
    print("\n=== Building for Windows ===")
    
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-
# ONE FILE BUILD - No separate uninstaller

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
    ],
    hookspath=[],
    hooksconfig={},
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
    icon='assets/icons/icon.ico',
    version='version.txt',
    onefile=True,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n[OK] Windows build complete!")
    print(f"  File: dist/FFmpegConverter.exe")
    print(f"  Size: ~43 MB")
    print(f"\n  User gets ONE file!")
    print(f"  To uninstall - just delete .exe")


def create_readme_dist():
    """Create README for distribution."""
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
    
    Path('dist/README.txt').write_text(readme, encoding='utf-8')


def main():
    system = platform.system()
    
    print(f"Building FFmpegGUI for {system}")
    print("=" * 50)
    
    Path('dist').mkdir(exist_ok=True)
    
    if system == 'Windows':
        build_windows()
    elif system == 'Linux':
        print("Linux build not implemented yet")
        sys.exit(1)
    elif system == 'Darwin':
        print("macOS build not implemented yet")
        sys.exit(1)
    else:
        print(f"Unsupported OS: {system}")
        sys.exit(1)
    
    create_readme_dist()
    
    print("\n" + "=" * 50)
    print("[OK] Build complete!")
    print(f"  Distribution in: dist/")


if __name__ == '__main__':
    main()
