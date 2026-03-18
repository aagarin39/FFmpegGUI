"""
macOS-специфичная реализация платформы.
"""
import subprocess
from pathlib import Path
from typing import Optional, Callable

from .base import Platform


class MacOSPlatform(Platform):
    """Реализация для macOS."""
    
    @property
    def name(self) -> str:
        return "macos"
    
    def get_ffmpeg_install_path(self) -> Path:
        """
        Получить путь для установки FFmpeg на macOS.
        
        Returns:
            Path: ~/Applications/FFmpegGUI
        """
        return Path.home() / "Applications" / "FFmpegGUI"
    
    def install_ffmpeg(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Установить FFmpeg на macOS.
        
        Предпочитает Homebrew.
        
        Args:
            url: URL для загрузки (не используется на macOS)
            progress_callback: Функция обратного вызова для прогресса
            
        Returns:
            bool: True если установка успешна
        """
        try:
            # Проверяем наличие Homebrew
            result = subprocess.run(
                ['which', 'brew'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("Homebrew not found. Please install from https://brew.sh")
                return False
            
            # Устанавливаем через Homebrew
            result = subprocess.run(
                ['brew', 'install', 'ffmpeg'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("FFmpeg installation timed out")
            return False
        except Exception as e:
            print(f"macOS FFmpeg installation error: {e}")
            return False
    
    def add_to_path(self, path: Path) -> bool:
        """
        Добавить путь в PATH на macOS.
        
        Добавляет в ~/.zprofile (macOS Catalina+ использует zsh).
        
        Args:
            path: Путь для добавления
            
        Returns:
            bool: True если успешно
        """
        try:
            path_str = f'\nexport PATH="$PATH:{str(path)}"\n'
            
            # macOS Catalina+ использует zsh по умолчанию
            config_files = [
                Path.home() / ".zprofile",
                Path.home() / ".zshrc",
                Path.home() / ".bash_profile",
                Path.home() / ".profile",
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    content = config_file.read_text()
                    if str(path) not in content:
                        config_file.write_text(content + path_str)
                    return True
            
            # Создаём .zprofile если не найден
            Path.home().joinpath(".zprofile").write_text(path_str)
            return True
            
        except Exception as e:
            print(f"Failed to add to PATH: {e}")
            return False
    
    def get_config_dir(self) -> Path:
        """
        Получить директорию для конфигурации на macOS.
        
        Returns:
            Path: ~/Library/Application Support/FFmpegGUI
        """
        return Path.home() / "Library" / "Application Support" / "FFmpegGUI"
    
    def open_file_explorer(self, path: Path) -> bool:
        """
        Открыть Finder на macOS.
        
        Args:
            path: Путь для открытия
            
        Returns:
            bool: True если успешно
        """
        try:
            subprocess.run(['open', str(path)], check=True)
            return True
        except Exception as e:
            print(f"Failed to open Finder: {e}")
            return False
