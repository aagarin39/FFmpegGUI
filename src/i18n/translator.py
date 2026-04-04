"""Translation loader and manager."""

import sys
import json
from pathlib import Path
from PyQt6.QtCore import QObject, QLocale, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from .locale import get_available_languages


class Translator(QObject):
    _instance = None
    _signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._current_lang = "ru"
        self.translations = {}
        self.current_locale = None
        self.AVAILABLE_LANGUAGES = get_available_languages()

    @classmethod
    def get_instance(cls) -> "Translator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_language(self, lang_code: str) -> bool:
        """Switch language instantly."""
        if lang_code not in self.AVAILABLE_LANGUAGES:
            return False
        
        # Загружаем переводы если ещё не загружены
        if lang_code not in self.translations:
            self._load_locale(lang_code)
        
        # Проверяем что загрузились успешно
        if lang_code in self.translations:
            self._current_lang = lang_code
            self.current_locale = self.translations[lang_code]
            self._signal.emit(lang_code)
            return True
        
        return False
    
    def _load_locale(self, lang_code: str) -> dict:
        """Load translations from .qm (JSON) file."""
        if getattr(sys, 'frozen', False):
            # PyInstaller onefile извлекает ресурсы в sys._MEIPASS
            resource_path = Path(sys._MEIPASS) / "translations"
        else:
            resource_path = Path(__file__).parent.parent.parent / "translations"
        
        qm_file = resource_path / f"{lang_code}.qm"
        print(f"Loading translations from: {qm_file}")
        
        if not qm_file.exists():
            print(f"Translation file not found: {qm_file}")
            return {}
        
        try:
            with open(qm_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.translations[lang_code] = data.get("translations", {})
                print(f"Loaded {len(self.translations[lang_code])} translations for {lang_code}")
                return self.translations[lang_code]
        except Exception as e:
            print(f"Error loading {qm_file}: {e}")
            return {}
    
    def switch_language(self, lang_code: str):
        """Thread-safe language switch via main thread."""
        if hasattr(self, 'app') and self.app:
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
