"""
Модуль управления обновлениями FFmpeg.
"""

import json
import time
import urllib.request
from pathlib import Path


class FFmpegUpdater:
    """Управление обновлениями FFmpeg"""
    
    CACHE_FILE = Path.home() / "FFmpegGUI" / "update_cache.json"
    SETTINGS_FILE = Path.home() / "FFmpegGUI" / "settings.json"
    CHECK_INTERVAL = 7 * 24 * 60 * 60  # 7 дней в секундах
    
    @classmethod
    def check_for_update(cls) -> dict | None:
        """
        Проверить наличие новой версии.
        Возвращает None если обновлений нет или
        dict с информацией о новой версии.
        """
        # Проверяем кэш
        cache = cls._load_cache()
        if cache and (time.time() - cache.get('checked_at', 0)) < cls.CHECK_INTERVAL:
            return None  # Ещё не время проверять
        
        try:
            # Запрос к GitHub API
            url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
            response = urllib.request.urlopen(url, timeout=10)
            data = json.loads(response.read())
            
            latest_version = data['tag_name']
            latest_date = data['published_at']
            
            # Получаем текущую версию
            from .ffmpeg_installer import FFmpegInstaller
            current_version = FFmpegInstaller.get_ffmpeg_version()
            
            # Сравниваем версии
            has_update = latest_version != current_version
            
            # Сохраняем в кэш
            cls._save_cache({
                'checked_at': time.time(),
                'latest_version': latest_version,
                'latest_date': latest_date,
                'has_update': has_update
            })
            
            if has_update:
                return {
                    'version': latest_version,
                    'date': latest_date,
                    'url': data['html_url']
                }
            
            return None
            
        except Exception as e:
            print(f"Update check failed: {e}")
            return None
    
    @classmethod
    def should_notify(cls) -> bool:
        """Проверить стоит ли показывать уведомление"""
        # Проверяем настройки
        settings = cls._load_settings()
        if settings.get('suppress_update_notifications'):
            return False
        
        # Проверяем наличие обновления
        update_info = cls.check_for_update()
        return update_info is not None
    
    @classmethod
    def get_update_info(cls) -> dict | None:
        """Получить информацию об обновлении"""
        cache = cls._load_cache()
        if cache and cache.get('has_update'):
            return {
                'version': cache['latest_version'],
                'date': cache['latest_date']
            }
        return None
    
    @classmethod
    def suppress_notifications(cls, suppress: bool):
        """Включить/выключить уведомления"""
        settings = cls._load_settings()
        settings['suppress_update_notifications'] = suppress
        cls._save_settings(settings)
    
    @classmethod
    def reset_notifications(cls):
        """Сбросить настройку уведомлений"""
        settings = cls._load_settings()
        settings['suppress_update_notifications'] = False
        cls._save_settings(settings)
    
    @classmethod
    def _load_cache(cls) -> dict | None:
        """Загрузить кэш"""
        if cls.CACHE_FILE.exists():
            try:
                return json.loads(cls.CACHE_FILE.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    @classmethod
    def _save_cache(cls, data: dict):
        """Сохранить кэш"""
        cls.CACHE_FILE.parent.mkdir(exist_ok=True)
        cls.CACHE_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    @classmethod
    def _load_settings(cls) -> dict:
        """Загрузить настройки"""
        if cls.SETTINGS_FILE.exists():
            try:
                return json.loads(cls.SETTINGS_FILE.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    @classmethod
    def _save_settings(cls, data: dict):
        """Сохранить настройки"""
        cls.SETTINGS_FILE.parent.mkdir(exist_ok=True)
        cls.SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
