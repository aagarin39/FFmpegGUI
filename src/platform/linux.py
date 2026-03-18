"""
Linux-специфичная реализация платформы.

Поддерживает как X11, так и Wayland.
"""
import subprocess
import os
from pathlib import Path
from typing import Optional, Callable

from .base import Platform


class LinuxPlatform(Platform):
    """Реализация для Linux."""
    
    @property
    def name(self) -> str:
        return "linux"
    
    def get_ffmpeg_install_path(self) -> Path:
        """
        Получить путь для установки FFmpeg на Linux.
        
        Returns:
            Path: ~/.local/FFmpegGUI/bin
        """
        return Path.home() / ".local" / "FFmpegGUI" / "bin"
    
    def install_ffmpeg(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Установить FFmpeg на Linux.
        
        Предпочитает системный пакетный менеджер.
        
        Args:
            url: URL для загрузки (не используется на Linux)
            progress_callback: Функция обратного вызова для прогресса
            
        Returns:
            bool: True если установка успешна
        """
        try:
            # Пробуем различные пакетные менеджеры
            package_managers = [
                ['apt', 'install', '-y', 'ffmpeg'],           # Debian/Ubuntu
                ['dnf', 'install', '-y', 'ffmpeg'],            # Fedora
                ['pacman', '-S', '--noconfirm', 'ffmpeg'],     # Arch
                ['zypper', 'install', '-y', 'ffmpeg'],         # openSUSE
            ]
            
            for cmd in package_managers:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if result.returncode == 0:
                        return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            return False
        except Exception as e:
            print(f"Linux FFmpeg installation error: {e}")
            return False
    
    def add_to_path(self, path: Path) -> bool:
        """
        Добавить путь в PATH на Linux.
        
        Добавляет в ~/.bashrc или ~/.profile.
        
        Args:
            path: Путь для добавления
            
        Returns:
            bool: True если успешно
        """
        try:
            path_str = f'\nexport PATH="$PATH:{str(path)}"\n'
            
            # Пробуем разные файлы конфигурации
            config_files = [
                Path.home() / ".bashrc",
                Path.home() / ".profile",
                Path.home() / ".zprofile",  # Для zsh
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    content = config_file.read_text()
                    if str(path) not in content:
                        config_file.write_text(content + path_str)
                    return True
            
            # Если ни один файл не найден, создаём .bashrc
            Path.home().joinpath(".bashrc").write_text(path_str)
            return True
            
        except Exception as e:
            print(f"Failed to add to PATH: {e}")
            return False
    
    def get_config_dir(self) -> Path:
        """
        Получить директорию для конфигурации на Linux.
        
        Returns:
            Path: ~/.config/FFmpegGUI (XDG Standard)
        """
        # Используем XDG Base Directory Specification
        xdg_config = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / "FFmpegGUI"
        return Path.home() / ".config" / "FFmpegGUI"
    
    def open_file_explorer(self, path: Path) -> bool:
        """
        Открыть файловый менеджер на Linux.
        
        Поддерживает различные файловые менеджеры.
        
        Args:
            path: Путь для открытия
            
        Returns:
            bool: True если успешно
        """
        try:
            # Пробуем различные файловые менеджеры
            file_managers = [
                ['xdg-open', str(path)],      # Универсальный
                ['nautilus', str(path)],      # GNOME
                ['dolphin', str(path)],       # KDE
                ['thunar', str(path)],        # XFCE
                ['pcmanfm', str(path)],       # LXDE
            ]
            
            for cmd in file_managers:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            return False
        except Exception as e:
            print(f"Failed to open file explorer: {e}")
            return False
    
    def is_wayland(self) -> bool:
        """
        Проверить используется ли Wayland.
        
        Returns:
            bool: True если Wayland
        """
        return bool(os.environ.get('WAYLAND_DISPLAY'))
