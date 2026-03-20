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
    
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main_pyqt.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'pydantic',
        'pydantic_core',
        'src.core.ffmpeg',
        'src.core.presets',
        'src.core.ffmpeg_installer',
        'src.core.ffmpeg_updater',
        'src.platforms',
        'urllib.request',
        'zipfile',
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
    onefile=True,
)

# Деинсталлятор программы (отдельный EXE для Panel Control)
uninstall_analysis = Analysis(
    ['src/uninstall.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

uninstall_exe = EXE(
    pyz,
    uninstall_analysis.scripts,
    uninstall_analysis.binaries,
    uninstall_analysis.zipfiles,
    uninstall_analysis.datas,
    [],
    name='FFmpegConverter_Uninstall',
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
    onefile=True,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n[OK] Windows сборка завершена!")
    print(f"  Программа: dist/FFmpegConverter.exe")
    print(f"  Деинсталлятор: dist/FFmpegConverter_Uninstall.exe")


def build_linux():
    """Сборка под Linux."""
    print("\n=== Сборка под Linux ===")
    
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main_ctk.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.Image',
        'darkdetect',
        'pydantic',
        'pydantic_core',
        'src.core.ffmpeg',
        'src.core.presets',
        'src.core.ffmpeg_installer',
        'urllib.request',
        'zipfile',
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
    onefile=True,
)
"""
    
    with open('ffmpeggui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    run_command([sys.executable, '-m', 'PyInstaller', 'ffmpeggui.spec', '--clean'])
    
    print("\n[OK] Linux сборка завершена!")
    print(f"  Бинарник: dist/FFmpegConverter")


def build_macos():
    """Сборка под macOS (.app)."""
    print("\n=== Сборка под macOS ===")
    
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main_ctk.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.Image',
        'darkdetect',
        'pydantic',
        'pydantic_core',
        'src.core.ffmpeg',
        'src.core.presets',
        'src.core.ffmpeg_installer',
        'urllib.request',
        'zipfile',
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
    
    print("\n[OK] macOS сборка завершена!")
    print(f"  App файл: dist/FFmpegConverter.app")


def create_readme_dist():
    """Создать README для дистрибутива."""
    readme = """================================================================================
                         FFmpeg Converter v0.3.0
================================================================================

Установка и запуск
------------------

1. Установите FFmpeg (при первом запуске):
   - Запустите FFmpegConverter.exe
   - Нажмите кнопку "Установить FFmpeg"
   - Создайте ярлык удаления (рекомендуется)
   - Дождитесь завершения (~30-60 секунд)

2. Использование:
   - Выберите папку с видео/фото
   - Выберите пресет
   - Нажмите "Конвертировать"

Удаление FFmpeg (~500 MB)
-------------------------

Ярлык на рабочем столе:
   - "Удалить FFmpeg.lnk" → дважды кликните

Или в программе:
   - Клик на статус "FFmpeg X.X"
   - "Удалить FFmpeg"

Файлы в дистрибутиве
--------------------

- FFmpegConverter.exe (43 MB) - Программа
- FFmpegConverter_Uninstall.exe (40 MB) - Деинсталлятор
- Cleanup_FFmpeg.exe (40 MB) - Удаление FFmpeg

Данные: %USERPROFILE%/FFmpegGUI/

Репозиторий: https://github.com/aagarin39/FFmpegGUI.git
Лицензия: MIT
================================================================================
"""
    
    Path('dist/README.txt').write_text(readme, encoding='utf-8')


def main():
    system = platform.system()
    
    print(f"Сборка FFmpegGUI для {system}")
    print("=" * 50)
    
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
    
    create_readme_dist()
    
    print("\n" + "=" * 50)
    print("[OK] Сборка завершена!")
    print(f"  Дистрибутив в папке: dist/")


if __name__ == '__main__':
    main()
