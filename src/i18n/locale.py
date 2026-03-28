"""OS locale detection logic."""

import sys
from PyQt6.QtCore import QLocale


def detect_locale() -> str:
    """Detect user's OS locale and map to supported languages."""
    
    system_locale = QLocale.system().name()
    
    locale_map = {
        "ru": "ru",
        "ru_RU": "ru",
        "en": "en",
        "en_US": "en",
        "en_GB": "en",
        "de": "en",
        "fr": "en",
        "es": "en",
    }
    
    if system_locale in locale_map:
        return locale_map[system_locale]
    
    if sys.platform == "win32":
        import ctypes
        try:
            user_locale = ctypes.windll.kernel32.GetUserDefaultLocaleName()
            if user_locale and user_locale in locale_map:
                return locale_map[user_locale]
        except Exception:
            pass
    
    elif sys.platform == "linux":
        import subprocess
        try:
            result = subprocess.run(
                ["locale", "-a"], 
                capture_output=True, 
                text=True
            )
            if any("ru" in line.lower() for line in result.stdout.split("\n")):
                return "ru"
        except Exception:
            pass
    
    elif sys.platform == "darwin":
        import subprocess
        try:
            result = subprocess.run(
                ["defaults", "read", "NSGlobalDomain", "AppleLocale"],
                capture_output=True, 
                text=True
            )
            locale_name = result.stdout.strip()
            if locale_name in locale_map:
                return locale_map[locale_name]
        except Exception:
            pass
    
    return "ru"


def get_available_languages() -> dict[str, dict]:
    """Get list of available languages with metadata."""
    return {
        "ru": {"name": "Русский", "code": "ru"},
        "en": {"name": "English", "code": "en"},
    }
