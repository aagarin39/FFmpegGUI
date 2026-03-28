"""Internationalization module for FFmpegGUI."""

from .translator import Translator
from .locale import detect_locale, get_available_languages

__all__ = ["Translator", "detect_locale", "get_available_languages"]
