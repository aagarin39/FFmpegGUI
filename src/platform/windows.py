"""
Windows-специфичная реализация платформы.
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable

from .base import Platform


class WindowsPlatform(Platform):
    """Реализация для Windows."""
    
    @property
    def name(self) -> str:
        return "windows"
    
    def get_ffmpeg_install_path(self) -> Path:
        """
        Получить путь для установки FFmpeg на Windows.
        
        Returns:
            Path: %USERPROFILE%\FFmpegGUI\ffmpeg
        """
        return Path.home() / "FFmpegGUI" / "ffmpeg"
    
    def install_ffmpeg(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Установить FFmpeg на Windows.
        
        Args:
            url: URL для загрузки
            progress_callback: Функция обратного вызова для прогресса
            
        Returns:
            bool: True если установка успешна
        """
        try:
            # Импорт локально чтобы не ломать другие платформы
            from ..core.ffmpeg_installer import FFmpegInstaller
            
            install_dir = self.get_ffmpeg_install_path()
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Используем существующий установщик
            def callback(status: str, percent: float):
                if progress_callback:
                    progress_callback(status, percent)
            
            return FFmpegInstaller.install(callback)
        except Exception as e:
            print(f"Windows FFmpeg installation error: {e}")
            return False
    
    def add_to_path(self, path: Path) -> bool:
        """
        Добавить путь в PATH системы Windows.
        
        Args:
            path: Путь для добавления
            
        Returns:
            bool: True если успешно
        """
        try:
            # Используем setx для добавления в PATH пользователя
            cmd = ['setx', 'PATH', f'%PATH%;{str(path)}']
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to add to PATH: {e}")
            return False
    
    def get_config_dir(self) -> Path:
        """
        Получить директорию для конфигурации на Windows.
        
        Returns:
            Path: %APPDATA%\FFmpegGUI
        """
        # Используем APPDATA для конфигурации
        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "FFmpegGUI"
    
    def open_file_explorer(self, path: Path) -> bool:
        """
        Открыть проводник Windows в указанной директории.
        
        Args:
            path: Путь для открытия
            
        Returns:
            bool: True если успешно
        """
        try:
            subprocess.run(['explorer', str(path)], check=True)
            return True
        except Exception as e:
            print(f"Failed to open explorer: {e}")
            return False
