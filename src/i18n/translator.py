"""Translation loader and manager."""

import sys
import json
from pathlib import Path
from PyQt6.QtCore import QLocale, QTimer
from PyQt6.QtWidgets import QApplication

from .locale import get_available_languages


class Translator:
    """Centralized translation manager using JSON-based translations."""
    
    AVAILABLE_LANGUAGES = {
        "ru": {"name": "Русский", "code": "ru"},
        "en": {"name": "English", "code": "en"},
    }
    
    _instance = None
    
    def __init__(self, app: QApplication = None):
        self.app = app or QApplication.instance()
        self.current_locale = QLocale.system()
        self.translations: dict[str, dict[str, str]] = {}
        self._current_lang = "ru"
        self._load_translations()
    
    @classmethod
    def get_instance(cls, app: QApplication = None) -> "Translator":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(app)
        return cls._instance
    
    def _get_resource_path(self) -> Path:
        """Get path to translation files."""
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS) / "translations"
        else:
            return Path(__file__).parent.parent.parent / "translations"
    
    def _load_translations(self):
        """Load all .qm files (JSON format)."""
        resource_path = self._get_resource_path()
        
        for lang_code in self.AVAILABLE_LANGUAGES:
            qm_file = resource_path / f"{lang_code}.qm"
            
            if qm_file.exists():
                try:
                    with open(qm_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.translations[lang_code] = data.get("translations", {})
                except Exception as e:
                    print(f"Error loading {lang_code}.qm: {e}")
    
    def get_current_language(self) -> str:
        """Get current language code."""
        return self._current_lang
    
    def set_language(self, lang_code: str) -> bool:
        """Switch language instantly."""
        if lang_code not in self.AVAILABLE_LANGUAGES:
            return False
        
        if lang_code in self.translations:
            self._current_lang = lang_code
            self.current_locale = QLocale(lang_code)
            return True
        
        return False
    
    def switch_language(self, lang_code: str):
        """Thread-safe language switch via main thread."""
        if self.app:
            QTimer.singleShot(0, lambda: self._switch_safe(lang_code))
        else:
            self.set_language(lang_code)
    
    def _switch_safe(self, lang_code: str):
        """Safe switch in main thread."""
        self.set_language(lang_code)
    
    def tr(self, text: str) -> str:
        """Translate text to current language."""
        if self._current_lang in self.translations:
            return self.translations[self._current_lang].get(text, text)
        return text
    
    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name."""
        return self.AVAILABLE_LANGUAGES.get(lang_code, {}).get("name", lang_code)
