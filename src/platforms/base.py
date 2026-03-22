"""
Базовый класс для всех платформ.

Определяет интерфейс для платформо-специфичной реализации.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable


class Platform(ABC):
    """Абстрактный базовый класс для платформ."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Название платформы (windows, linux, macos)."""
        pass
    
    @abstractmethod
    def get_ffmpeg_install_path(self) -> Path:
        """
        Получить путь для установки FFmpeg.
        
        Returns:
            Path: Путь к директории для FFmpeg
        """
        pass
    
    @abstractmethod
    def install_ffmpeg(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Установить FFmpeg.
        
        Args:
            url: URL для загрузки
            progress_callback: Функция обратного вызова для прогресса
            
        Returns:
            bool: True если установка успешна
        """
        pass
    
    @abstractmethod
    def add_to_path(self, path: Path) -> bool:
        """
        Добавить путь в PATH системы.
        
        Args:
            path: Путь для добавления
            
        Returns:
            bool: True если успешно
        """
        pass
    
    @abstractmethod
    def get_config_dir(self) -> Path:
        """
        Получить директорию для конфигурации приложения.
        
        Returns:
            Path: Путь к директории конфигурации
        """
        pass
    
    @abstractmethod
    def open_file_explorer(self, path: Path) -> bool:
        """
        Открыть файловый менеджер в указанной директории.
        
        Args:
            path: Путь для открытия
            
        Returns:
            bool: True если успешно
        """
        pass
    
    def is_wayland(self) -> bool:
        """
        Проверить используется ли Wayland (для Linux).
        
        Returns:
            bool: True если Wayland
        """
        return False
