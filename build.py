#!/usr/bin/env python3
"""
Скрипт для сборки нативных приложений под все платформы.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def run_command(cmd: list[str], cwd: str = None):
    """Выполнить команду и вывести результат."""
    print(f"Выполнение: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise Exception(f"Команда вернула код {result.returncode}")
    return result


def build_windows():
    """Сборка под Windows (.exe)."""
    print("\n=== Сборка под Windows ===")
    
    # Создаём spec файл
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'flet',
        'flet.core',
        'flet.core.page',
        'flet.core.control',
        'flet.core.controls',
        'flet.core.app',
        'flet.controls',
        'flet.controls.material',
        'flet.controls.services',
        'flet.controls.services.file_picker',
        'pydantic',
        'pydantic_core',
        'pydantic.dataclasses',
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
    icon=None,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # Запускаем PyInstaller
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n✓ Windows сборка завершена!")
    print(f"  EXE файл: dist/FFmpegConverter.exe")


def build_linux():
    """Сборка под Linux (AppImage/.deb)."""
    print("\n=== Сборка под Linux ===")
    
    # Создаём spec файл для Linux
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'flet',
        'flet.core',
        'flet.core.page',
        'flet.core.control',
        'flet.core.controls',
        'flet.core.app',
        'flet.controls',
        'flet.controls.material',
        'flet.controls.services',
        'flet.controls.services.file_picker',
        'pydantic',
        'pydantic_core',
        'pydantic.dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
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
    icon=None,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n✓ Linux сборка завершена!")
    print(f"  Бинарник: dist/FFmpegConverter")
    
    # Создаём .desktop файл
    desktop_content = """[Desktop Entry]
Name=FFmpeg Converter
Comment=Кроссплатформенный конвертер видео
Exec=FFmpegConverter
Icon=ffmpegconverter
Type=Application
Categories=AudioVideo;Video;
"""
    
    Path('dist/ffmpegconverter.desktop').write_text(desktop_content)
    print(f"  Desktop файл: dist/ffmpegconverter.desktop")


def build_macos():
    """Сборка под macOS (.app)."""
    print("\n=== Сборка под macOS ===")
    
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'flet',
        'flet.core',
        'flet.core.page',
        'flet.core.control',
        'flet.core.controls',
        'flet.core.app',
        'flet.controls',
        'flet.controls.material',
        'flet.controls.services',
        'flet.controls.services.file_picker',
        'pydantic',
        'pydantic_core',
        'pydantic.dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = APP(
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
    icon=None,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean', '--windowed'])
    
    print("\n✓ macOS сборка завершена!")
    print(f"  App файл: dist/FFmpegConverter.app")


def create_readme_dist():
    """Создать README для дистрибутива."""
    readme = """# FFmpeg Converter

## Установка FFmpeg

### Windows
1. Скачайте FFmpeg с https://www.gyan.dev/ffmpeg/builds/
2. Распакуйте ffmpeg.exe и ffprobe.exe в папку с приложением

### Linux
```bash
sudo apt install ffmpeg  # Debian/Ubuntu
sudo dnf install ffmpeg  # Fedora
sudo pacman -S ffmpeg    # Arch
```

### macOS
```bash
brew install ffmpeg
```

## Запуск

- **Windows**: Дважды кликните на FFmpegConverter.exe
- **Linux**: ./FFmpegConverter
- **macOS**: Откройте FFmpegConverter.app

## Лицензия
MIT
"""
    
    Path('dist/README.txt').write_text(readme)


def main():
    system = platform.system()
    
    print(f"Сборка FFmpegGUI для {system}")
    print("=" * 50)
    
    # Создаём папку dist
    Path('dist').mkdir(exist_ok=True)
    
    if system == 'Windows':
        build_windows()
    elif system == 'Linux':
        build_linux()
    elif system == 'Darwin':
        build_macos()
    else:
        print(f"Неподдерживаемая ОС: {system}")
        sys.exit(1)
    
    # Создаём README для дистрибутива
    create_readme_dist()
    
    print("\n" + "=" * 50)
    print("✓ Сборка завершена!")
    print(f"  Дистрибутив в папке: dist/")


if __name__ == '__main__':
    main()
