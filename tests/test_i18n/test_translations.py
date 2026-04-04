"""Tests for i18n translation coverage and correctness."""
import json
import re
from pathlib import Path

import pytest

TRANSLATIONS_DIR = Path(__file__).parent.parent.parent / "translations"
SRC_DIR = Path(__file__).parent.parent.parent / "src"


def load_qm(lang: str) -> dict:
    """Load translations from .qm file."""
    qm_path = TRANSLATIONS_DIR / f"{lang}.qm"
    assert qm_path.exists(), f"Translation file not found: {qm_path}"
    with open(qm_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("translations", {})


def extract_tr_strings_from_file(py_file: Path) -> set[str]:
    """Extract all self.tr('...') strings from a Python file."""
    import ast
    
    content = py_file.read_text(encoding='utf-8')
    tree = ast.parse(content)
    
    tr_strings = set()
    
    for node in ast.walk(tree):
        # Find self.tr(...) calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'tr':
                    # Check if it's self.tr()
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == 'self':
                            # Extract string argument
                            if node.args:
                                arg = node.args[0]
                                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                    tr_strings.add(arg.value)
                                elif isinstance(arg, ast.JoinedStr):
                                    # f-string - skip for now
                                    pass
    
    return tr_strings


class TestTranslationFilesExist:
    def test_en_qm_exists(self):
        assert (TRANSLATIONS_DIR / "en.qm").exists()
    
    def test_ru_qm_exists(self):
        assert (TRANSLATIONS_DIR / "ru.qm").exists()


class TestTranslationLoading:
    def test_en_loads_successfully(self):
        translations = load_qm("en")
        assert len(translations) > 0, "English translations should not be empty"
    
    def test_ru_loads_successfully(self):
        translations = load_qm("ru")
        assert len(translations) > 0, "Russian translations should not be empty"
    
    def test_en_and_ru_have_similar_count(self):
        en = load_qm("en")
        ru = load_qm("ru")
        # Should be within 10% of each other
        diff = abs(len(en) - len(ru))
        assert diff < max(len(en), len(ru)) * 0.1, \
            f"Translation count mismatch: en={len(en)}, ru={len(ru)}"


class TestNewlineHandling:
    def test_no_double_escaped_newlines_in_en(self):
        """Ensure \\n is not double-escaped in .qm files."""
        en = load_qm("en")
        for key, value in en.items():
            assert "\\\\n" not in key, f"Double-escaped \\n in key: {key!r}"
            assert "\\\\n" not in value, f"Double-escaped \\n in value: {value!r}"
    
    def test_newline_translation_works(self):
        """Test that strings with newlines are correctly translated."""
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        t.set_language("en")
        
        russian_text = "Выберите компоненты для удаления.\nЭто действие необратимо!"
        expected = "Select components to uninstall.\nThis action cannot be undone!"
        
        result = t.tr(russian_text)
        assert result == expected, f"Newline translation failed: got {result!r}"


class TestTranslationCoverage:
    def test_uninstall_dialog_strings_covered_en(self):
        """All self.tr() strings in uninstall.py should have English translations."""
        en = load_qm("en")
        uninstall_py = SRC_DIR / "uninstall.py"
        tr_strings = extract_tr_strings_from_file(uninstall_py)
        
        missing = []
        for s in tr_strings:
            if s not in en:
                missing.append(s)
        
        assert not missing, f"Missing English translations for uninstall.py:\n" + \
            "\n".join(f"  - {s!r}" for s in missing[:10])
    
    def test_uninstall_dialog_strings_covered_ru(self):
        """All self.tr() strings in uninstall.py should have Russian translations."""
        ru = load_qm("ru")
        uninstall_py = SRC_DIR / "uninstall.py"
        tr_strings = extract_tr_strings_from_file(uninstall_py)
        
        missing = []
        for s in tr_strings:
            if s not in ru:
                missing.append(s)
        
        assert not missing, f"Missing Russian translations for uninstall.py:\n" + \
            "\n".join(f"  - {s!r}" for s in missing[:10])


class TestSpecificTranslations:
    def test_delete_button_translated(self):
        """'Удалить' should be translated to 'Uninstall' in English."""
        en = load_qm("en")
        assert "Удалить" in en, "Missing translation for 'Удалить'"
        assert en["Удалить"] == "Uninstall", f"Expected 'Uninstall', got {en['Удалить']!r}"
    
    def test_cancel_button_translated(self):
        """'Отмена' should be translated to 'Cancel' in English."""
        en = load_qm("en")
        assert "Отмена" in en, "Missing translation for 'Отмена'"
        assert en["Отмена"] == "Cancel", f"Expected 'Cancel', got {en['Отмена']!r}"


class TestTranslatorClass:
    def test_singleton_returns_same_instance(self):
        from src.i18n.translator import Translator
        t1 = Translator.get_instance()
        t2 = Translator.get_instance()
        assert t1 is t2, "Translator should be a singleton"
    
    def test_switch_to_english(self):
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        ok = t.set_language("en")
        assert ok, "Should successfully switch to English"
        assert t._current_lang == "en"
    
    def test_switch_to_russian(self):
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        ok = t.set_language("ru")
        assert ok, "Should successfully switch to Russian"
        assert t._current_lang == "ru"
    
    def test_invalid_language_returns_false(self):
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        ok = t.set_language("invalid")
        assert not ok, "Should reject invalid language codes"
    
    def test_tr_returns_translation(self):
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        t.set_language("en")
        result = t.tr("Удалить")
        assert result == "Uninstall", f"Expected 'Uninstall', got {result!r}"
    
    def test_tr_falls_back_to_original(self):
        from src.i18n.translator import Translator
        t = Translator.get_instance()
        t.set_language("en")
        result = t.tr("This string does not exist")
        assert result == "This string does not exist", "Should fallback to original text"
