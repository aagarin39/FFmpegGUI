"""
FFmpeg Converter - PyQt6 версия
Стабильный интерфейс без дерганий на многомониторных системах
"""
import sys
import os
import shutil
import tempfile
import datetime
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFileDialog,
    QScrollArea, QFrame, QMessageBox, QGroupBox, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QMenu, QStatusBar, QDialog,
    QSlider, QListWidget, QListWidgetItem, QSizePolicy, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QAction

# Импорт i18n модуля
if getattr(sys, 'frozen', False):
    import src.i18n
    Translator = src.i18n.Translator
    detect_locale = src.i18n.detect_locale
    get_available_languages = src.i18n.get_available_languages
else:
    from src.i18n import Translator, detect_locale

def get_resource_path(relative_path: str) -> str:
    """Получить путь к ресурсу (иконки, изображения)"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


def get_window_icon_path() -> str:
    """Получить путь к иконке окна для текущей платформы."""
    system = platform.system()
    if system == 'Darwin':
        return get_resource_path("assets/icons/icon.icns")
    elif system == 'Windows':
        return get_resource_path("assets/icons/icon.ico")
    else:
        return get_resource_path("assets/icons/icon.png")


# Импорт модулей проекта
if getattr(sys, 'frozen', False):
    # Запущен как .exe (PyInstaller)
    import src.core.ffmpeg
    import src.core.ffmpeg_installer
    import src.core.ffmpeg_updater
    import src.core.presets
    import src.platforms
    
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
    PresetManager = src.core.presets.PresetManager
    Preset = src.core.presets.Preset
    FFmpegInstaller = src.core.ffmpeg_installer.FFmpegInstaller
    FFmpegUpdater = src.core.ffmpeg_updater.FFmpegUpdater
    PlatformManager = src.platforms.PlatformManager
else:
    # Запущен как .py (разработка)
    from src.core.ffmpeg import FFmpegWrapper
    from src.core.ffmpeg_installer import FFmpegInstaller
    from src.core.ffmpeg_updater import FFmpegUpdater
    from src.core.presets import PresetManager, Preset
    from src.platforms import PlatformManager


class WorkerThread(QThread):
    """Поток для фоновых задач"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, int, int)
    log = pyqtSignal(str)
    
    def __init__(self, files, output_folder, preset, ffmpeg, translator=None):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.preset = preset
        self.ffmpeg = ffmpeg
        self.translator = translator
        self.process = None  # Ссылка на subprocess.Popen
        self._cancel_flag = False
    
    def tr(self, text: str) -> str:
        """Translate text using translator."""
        if self.translator:
            return self.translator.tr(text)
        return text
    
    def kill(self):
        """Мгновенное завершение ffmpeg.exe"""
        self._cancel_flag = True
        try:
            if self.process and self.process.poll() is None:
                self.process.kill()
        except (ProcessLookupError, OSError):
            pass  # Процесс уже завершился
    
    def run(self):
        ok = 0
        err = 0
        
        for i, file in enumerate(self.files):
            if self._cancel_flag:
                self.log.emit(self.tr("⚠️ Конвертация отменена пользователем"))
                break
            
            name = Path(file).name
            self.log.emit(self.tr("▶ {name}").format(name=name))
            
            # Формируем краткое имя пресета: codec_accelerator
            codec = self.preset.codec_type  # h264, hevc
            accelerator = self.preset.hw_accelerator or "cpu"  # nvenc, qsv, amf, cpu
            preset_suffix = f"{codec}_{accelerator}"
            
            ext = self.preset.container if self.preset.container else "mkv"
            stem = Path(file).stem
            output = str(self.output_folder / f"{stem}.{preset_suffix}.{ext}")
            
            # Удаляем 0-байтный файл если существует (предыдущая неудачная конвертация)
            output_path = Path(output)
            if output_path.exists() and output_path.stat().st_size == 0:
                try:
                    output_path.unlink()
                    self.log.emit(self.tr("🗑️ Удалён пустой файл: {name}").format(name=output_path.name))
                except Exception as e:
                    self.log.emit(self.tr("⚠️ Не удалось удалить пустой файл: {error}").replace("{error}", str(e)))
            
            try:
                if self.ffmpeg.convert(file, output, self.preset, self):
                    # Проверяем что файл не пустой
                    if output_path.exists() and output_path.stat().st_size == 0:
                        err += 1
                        self.log.emit(self.tr("✗ {name}: Файл пустой (кодек не доступен)").format(name=name))
                    else:
                        ok += 1
                        self.log.emit(self.tr("✓ {name}").format(name=name))
                else:
                    if self._cancel_flag:
                        break
                    err += 1
                    self.log.emit(self.tr("✗ {name}").format(name=name))
            except Exception as e:
                err += 1
                self.log.emit(self.tr("✗ {name}: {error}").format(name=name, error=e))
            
            self.progress.emit(i + 1, name)
        
        self.finished.emit(ok == err == 0, ok, err)


class InstallerThread(QThread):
    """Поток установки FFmpeg"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    
    def run(self):
        def cb(status, pct):
            self.progress.emit(int(pct))
        result = FFmpegInstaller.install(cb)
        self.finished.emit(result)


class PresetBuilderDialog(QDialog):
    """Диалог конструктора пресетов с подробными описаниями"""
    
    def __init__(self, parent, preset_manager):
        super().__init__(parent)
        self.preset_manager = preset_manager
        self.current_preset = None
        self.translator = Translator.get_instance()
        self._init_ui()
        self._load_presets_list()
    
    def tr(self, text: str) -> str:
        """Translate text to current language."""
        return self.translator.tr(text)
    
    def _init_ui(self):
        self.setWindowTitle(self.tr("Конструктор пресетов"))
        self.setMinimumSize(900, 650)
        self.resize(900, 650)
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        
        # Левая панель: Список пресетов
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel(self.tr("<b>Сохранённые пресеты</b>")))
        
        self.presets_list = QListWidget()
        self.presets_list.setMinimumHeight(200)
        self.presets_list.itemSelectionChanged.connect(self._load_selected_preset)
        left_layout.addWidget(self.presets_list)
        
        # Кнопки управления
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.new_btn = QPushButton(self.tr("➕ Новый"))
        self.new_btn.clicked.connect(self._new_preset)
        btn_layout.addWidget(self.new_btn)
        
        self.save_btn = QPushButton(self.tr("💾 Сохранить"))
        self.save_btn.setStyleSheet("background-color: #15803d; color: white;")
        self.save_btn.clicked.connect(self._save_preset)
        btn_layout.addWidget(self.save_btn)
        
        self.delete_btn = QPushButton(self.tr("🗑️ Удалить"))
        self.delete_btn.setStyleSheet("background-color: #dc2626; color: white;")
        self.delete_btn.clicked.connect(self._delete_preset)
        btn_layout.addWidget(self.delete_btn)
        
        self.reset_btn = QPushButton(self.tr("🔄 Сбросить"))
        self.reset_btn.setStyleSheet("background-color: #0891b2; color: white;")
        self.reset_btn.clicked.connect(self._reset_presets)
        btn_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(btn_frame)
        left_layout.addStretch()
        
        # Информация
        info_box = QGroupBox(self.tr("Справка"))
        info_layout = QVBoxLayout(info_box)
        self.help_label = QLabel(self.tr("Выберите пресет или создайте новый"))
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        info_layout.addWidget(self.help_label)
        left_layout.addWidget(info_box)
        
        layout.addWidget(left_panel, 1)
        
        # Правая панель: Форма
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        form_widget = QWidget()
        self.form_layout = QFormLayout(form_widget)
        self.form_layout.setSpacing(12)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        right_panel.setWidget(form_widget)
        layout.addWidget(right_panel, 2)
        
        # Поля формы
        self._create_form_fields()
    
    def _create_form_fields(self):
        """Создать поля формы с подсказками"""
        # Название
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("Введите название пресета"))
        self.name_input.textChanged.connect(lambda: self._show_help("name"))
        self.form_layout.addRow(self.tr("Название*"), self.name_input)
        
        # Описание
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(self.tr("Краткое описание"))
        self.desc_input.textChanged.connect(lambda: self._show_help("desc"))
        self.form_layout.addRow(self.tr("Описание"), self.desc_input)
        
        self.form_layout.addRow(QLabel("<hr/>"))
        
        # Ускорение
        self.hw_input = QComboBox()
        self.hw_input.addItems([
            self.tr("nvenc (NVIDIA)"),
            self.tr("qsv (Intel)"),
            self.tr("amf (AMD)"),
            self.tr("cpu (CPU)"),
        ])
        self.hw_input.currentTextChanged.connect(lambda: self._show_help("hw"))
        self.form_layout.addRow(self.tr("Ускорение*"), self.hw_input)
        
        # Кодек
        self.codec_input = QComboBox()
        self.codec_input.addItems([
            self.tr("H.264 (совместимость)"),
            self.tr("H.265/HEVC (эффективность)"),
        ])
        self.codec_input.currentTextChanged.connect(lambda: self._show_help("codec"))
        self.form_layout.addRow(self.tr("Кодек*"), self.codec_input)
        
        # Качество CQ
        cq_frame = QHBoxLayout()
        self.cq_slider = QSlider(Qt.Orientation.Horizontal)
        self.cq_slider.setMinimum(1)
        self.cq_slider.setMaximum(51)
        self.cq_slider.setValue(20)
        self.cq_slider.valueChanged.connect(self._update_cq_label)
        
        self.cq_label = QLabel("20")
        self.cq_label.setMinimumWidth(30)
        self.cq_label.setStyleSheet("font-weight: bold; color: #22c55e;")
        
        cq_frame.addWidget(self.cq_slider)
        cq_frame.addWidget(self.cq_label)
        
        self.cq_slider.valueChanged.connect(lambda: self._show_help("cq"))
        self.form_layout.addRow(self.tr("Качество (CQ)*"), cq_frame)
        
        # Масштабирование
        self.scale_input = QComboBox()
        self.scale_input.addItems([
            self.tr("Нет (оригинал)"),
            self.tr("1920x Full HD"),
            self.tr("1280x HD"),
            self.tr("3840x 4K"),
        ])
        self.scale_input.currentTextChanged.connect(lambda: self._show_help("scale"))
        self.form_layout.addRow(self.tr("Масштаб"), self.scale_input)
        
        self.form_layout.addRow(QLabel("<hr/>"))
        
        # Аудио каналы
        self.audio_input = QComboBox()
        self.audio_input.addItems([
            self.tr("2 (Стерео)"),
            self.tr("6 (5.1 Surround)"),
            self.tr("8 (7.1 Surround)"),
        ])
        self.audio_input.currentTextChanged.connect(lambda: self._show_help("audio"))
        self.form_layout.addRow(self.tr("Аудио каналы*"), self.audio_input)
        
        # Контейнер
        self.container_input = QComboBox()
        self.container_input.addItems([
            self.tr("MKV (универсальный)"),
            self.tr("MP4 (совместимость)"),
        ])
        self.container_input.currentTextChanged.connect(lambda: self._show_help("container"))
        self.form_layout.addRow(self.tr("Контейнер*"), self.container_input)
        
        # Субтитры
        self.subs_input = QCheckBox(self.tr("Удалить субтитры из видео"))
        self.subs_input.stateChanged.connect(lambda: self._show_help("subs"))
        self.form_layout.addRow("", self.subs_input)
        
        # Индикатор изменений
        self.modified_label = QLabel("")
        self.modified_label.setStyleSheet("color: #f59e0b; font-style: italic;")
        self.form_layout.addRow("", self.modified_label)
        
        # Подключить отслеживание изменений
        self.name_input.textChanged.connect(self._on_modified)
        self.desc_input.textChanged.connect(self._on_modified)
        self.hw_input.currentTextChanged.connect(self._on_modified)
        self.codec_input.currentTextChanged.connect(self._on_modified)
        self.cq_slider.valueChanged.connect(self._on_modified)
        self.scale_input.currentTextChanged.connect(self._on_modified)
        self.audio_input.currentTextChanged.connect(self._on_modified)
        self.container_input.currentTextChanged.connect(self._on_modified)
        self.subs_input.stateChanged.connect(self._on_modified)
    
    def _show_help(self, key):
        """Показать справку по полю"""
        self._current_help_key = key
        self.help_label.setText(self.tr(f"help.{key}"))
    
    def _update_cq_label(self, value):
        """Обновить метку качества"""
        self.cq_label.setText(str(value))
        if value <= 22:
            self.cq_label.setStyleSheet("font-weight: bold; color: #22c55e;")
        elif value <= 30:
            self.cq_label.setStyleSheet("font-weight: bold; color: #f59e0b;")
        else:
            self.cq_label.setStyleSheet("font-weight: bold; color: #ef4444;")
    
    def _on_modified(self):
        """Отметить форму как изменённую"""
        if self.current_preset:
            self.modified_label.setText(self.tr("✏️ Изменено — сохраните пресет"))
        else:
            self.modified_label.setText(self.tr("✏️ Новый пресет — введите название и сохраните"))
    
    def _load_presets_list(self):
        """Загрузить список пресетов"""
        self.presets_list.clear()
        
        for p in self.preset_manager.get_all_presets():
            icon = "📦 " if p.id.startswith("custom_") else "🔒 "
            preset_name_key = f"preset.{p.id}.name"
            localized_name = self.tr(preset_name_key)
            if localized_name == preset_name_key:
                localized_name = p.name
            item = QListWidgetItem(f"{icon}{localized_name}")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.presets_list.addItem(item)
    
    def _load_selected_preset(self):
        """Загрузить выбранный пресет в форму"""
        items = self.presets_list.selectedItems()
        if not items:
            return
        
        preset_id = items[0].data(Qt.ItemDataRole.UserRole)
        preset = self.preset_manager.get_preset(preset_id)
        if not preset:
            return
        
        self.current_preset = preset
        self.modified_label.setText("")
        
        # Заполнить форму
        self.name_input.setText(preset.name)
        self.desc_input.setText(preset.description)
        
        # Ускорение
        hw_map = {"nvenc": 0, "qsv": 1, "amf": 2, None: 3}
        self.hw_input.setCurrentIndex(hw_map.get(preset.hw_accelerator, 3))
        
        # Кодек
        codec_idx = 0 if preset.codec_type == "h264" else 1
        self.codec_input.setCurrentIndex(codec_idx)
        
        # Качество
        self.cq_slider.setValue(preset.cq)
        
        # Масштаб
        scale_map = {"": 0, "1920:-2": 1, "1280:-2": 2, "3840:-2": 3}
        self.scale_input.setCurrentIndex(scale_map.get(preset.scale, 0))
        
        # Аудио
        audio_map = {"2": 0, "6": 1, "8": 2}
        self.audio_input.setCurrentIndex(audio_map.get(str(preset.audio_channels), 0))
        
        # Контейнер
        container_idx = 0 if preset.container == "mkv" else 1
        self.container_input.setCurrentIndex(container_idx)
        
        # Субтитры
        self.subs_input.setChecked(preset.remove_subtitles)
        
        self._show_help("name")
    
    def _new_preset(self):
        """Очистить форму для нового пресета"""
        self.current_preset = None
        self.presets_list.clearSelection()
        self.name_input.clear()
        self.desc_input.clear()
        self.hw_input.setCurrentIndex(0)
        self.codec_input.setCurrentIndex(0)
        self.cq_slider.setValue(20)
        self.scale_input.setCurrentIndex(0)
        self.audio_input.setCurrentIndex(0)
        self.container_input.setCurrentIndex(0)
        self.subs_input.setChecked(False)
        self.modified_label.setText("✏️ Новый пресет — введите название и сохраните")
        self._show_help("name")
    
    def _get_preset_from_form(self):
        """Получить данные пресета из формы"""
        name = self.name_input.text().strip()
        if not name:
            return None
        
        # Парсинг значений
        hw_map = {0: "nvenc", 1: "qsv", 2: "amf", 3: None}
        hw = hw_map.get(self.hw_input.currentIndex())
        
        codec = "h264" if self.codec_input.currentIndex() == 0 else "hevc"
        
        scale_map = {0: "", 1: "1920:-2", 2: "1280:-2", 3: "3840:-2"}
        scale = scale_map.get(self.scale_input.currentIndex())
        
        audio_map = {0: 2, 1: 6, 2: 8}
        audio = audio_map.get(self.audio_input.currentIndex(), 2)
        
        container = "mkv" if self.container_input.currentIndex() == 0 else "mp4"
        
        # ID для пользовательских пресетов
        if self.current_preset and self.current_preset.id.startswith("custom_"):
            preset_id = self.current_preset.id
        else:
            preset_id = f"custom_{name.lower().replace(' ', '_')}"
        
        return Preset(
            id=preset_id,
            name=name,
            description=self.desc_input.text().strip(),
            hw_accelerator=hw,
            codec_type=codec,
            cq=self.cq_slider.value(),
            scale=scale if scale else None,
            audio_channels=audio,
            remove_subtitles=bool(self.subs_input.isChecked()),
            container=container,
        )
    
    def _save_preset(self):
        """Сохранить пресет"""
        preset = self._get_preset_from_form()
        if not preset:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Введите название пресета"))
            return
        
        # Проверка на встроенные пресеты
        if self.current_preset and not self.current_preset.id.startswith("custom_"):
            reply = QMessageBox.question(
                self, self.tr("Сохранение"),
                self.tr("Это встроенный пресет. Сохранить как новый?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.preset_manager.add_preset(preset)
        self._load_presets_list()
        self.modified_label.setText(self.tr("✓ Сохранено"))
        
        # Обновить комбобокс в главном окне
        if self.parent() and hasattr(self.parent(), 'preset_combo'):
            self.parent().preset_combo.blockSignals(True)
            self.parent().preset_combo.clear()
            for preset in self.preset_manager.get_all_presets():
                preset_name_key = f"preset.{preset.id}.name"
                localized_name = self.parent().tr(preset_name_key)
                if localized_name == preset_name_key:
                    localized_name = preset.name
                self.parent().preset_combo.addItem(localized_name, preset.id)
            self.parent().preset_combo.blockSignals(False)
    
    def _delete_preset(self):
        """Удалить выбранный пресет"""
        items = self.presets_list.selectedItems()
        if not items:
            QMessageBox.information(self, self.tr("Удаление"), self.tr("Сначала выберите пресет"))
            return
        
        if not self.current_preset:
            QMessageBox.information(self, self.tr("Удаление"), self.tr("Сначала выберите пресет"))
            return
        
        if not self.current_preset.id.startswith("custom_"):
            QMessageBox.warning(
                self, self.tr("Нельзя удалить"),
                self.tr("Встроенные пресеты удалять нельзя.\nСоздайте свой пресет с нужными параметрами.")
            )
            return
        
        reply = QMessageBox.question(
            self, self.tr("Подтверждение"),
            self.tr("Удалить пресет '{name}'?").format(name=self.current_preset.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.preset_manager.delete_preset(self.current_preset.id)
            self._load_presets_list()
            self._new_preset()
    
    def _reset_presets(self):
        """Восстановить стандартные пресеты"""
        reply = QMessageBox.question(
            self,
            self.tr("Восстановление пресетов"),
            self.tr("⚠️  Все пользовательские пресеты будут удалены.\nСтандартные пресеты будут восстановлены.\n\nПродолжить?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Удаляем файл пользовательских пресетов
        try:
            os.remove(self.preset_manager.config_path)
        except FileNotFoundError:
            pass
        
        # Пересоздаём менеджер пресетов - это загрузит стандартные
        self.preset_manager = PresetManager()
        self._load_presets_list()
        self._new_preset()
        
        # Обновить комбобокс в главном окне
        if self.parent() and hasattr(self.parent(), 'preset_combo'):
            self.parent().preset_combo.blockSignals(True)
            self.parent().preset_combo.clear()
            for preset in self.preset_manager.get_all_presets():
                preset_name_key = f"preset.{preset.id}.name"
                localized_name = self.parent().tr(preset_name_key)
                if localized_name == preset_name_key:
                    localized_name = preset.name
                self.parent().preset_combo.addItem(localized_name, preset.id)
            self.parent().preset_combo.blockSignals(False)
        
        QMessageBox.information(
            self,
            self.tr("Готово"),
            self.tr("✓ Стандартные пресеты восстановлены")
        )
    
    def _update_ui_text(self):
        """Обновить все тексты при переключении языка."""
        self.setWindowTitle(self.tr("Конструктор пресетов"))
        
        # Обновить поля формы
        self.name_input.setPlaceholderText(self.tr("Введите название пресета"))
        self.desc_input.setPlaceholderText(self.tr("Краткое описание"))
        
        # Обновить заголовки полей
        for i in range(self.form_layout.rowCount()):
            item = self.form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if item and item.widget():
                label = item.widget()
                if isinstance(label, QLabel):
                    text = label.text()
                    if text in ["Название*", "Описание", "Ускорение*", "Кодек*", "Качество (CQ)*", "Масштаб", "Аудио каналы*", "Контейнер*", ""]:
                        continue
        
        # Обновить комбобоксы
        if hasattr(self, 'hw_input'):
            self.hw_input.clear()
            self.hw_input.addItems([
                self.tr("nvenc (NVIDIA)"),
                self.tr("qsv (Intel)"),
                self.tr("amf (AMD)"),
                self.tr("cpu (CPU)"),
            ])
        
        if hasattr(self, 'codec_input'):
            self.codec_input.clear()
            self.codec_input.addItems([
                self.tr("H.264 (совместимость)"),
                self.tr("H.265/HEVC (эффективность)"),
            ])
        
        if hasattr(self, 'scale_input'):
            self.scale_input.clear()
            self.scale_input.addItems([
                self.tr("Нет (оригинал)"),
                self.tr("1920x Full HD"),
                self.tr("1280x HD"),
                self.tr("3840x 4K"),
            ])
        
        if hasattr(self, 'audio_input'):
            self.audio_input.clear()
            self.audio_input.addItems([
                self.tr("2 (Стерео)"),
                self.tr("6 (5.1 Surround)"),
                self.tr("8 (7.1 Surround)"),
            ])
        
        if hasattr(self, 'container_input'):
            self.container_input.clear()
            self.container_input.addItems([
                self.tr("MKV (универсальный)"),
                self.tr("MP4 (совместимость)"),
            ])
        
        # Обновить справку
        if self.help_label.text():
            current_key = self._current_help_key if hasattr(self, '_current_help_key') else "name"
            self.help_label.setText(self.tr(f"help.{current_key}"))
        
        # Обновить кнопки
        if hasattr(self, 'new_btn'):
            self.new_btn.setText(self.tr("➕ Новый"))
        if hasattr(self, 'save_btn'):
            self.save_btn.setText(self.tr("💾 Сохранить"))
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setText(self.tr("🗑️ Удалить"))
        if hasattr(self, 'reset_btn'):
            self.reset_btn.setText(self.tr("🔄 Сбросить"))
        if hasattr(self, 'help_label'):
            info_box = self.help_label.parent()
            if info_box:
                info_box.setTitle(self.tr("Справка"))
        
        # Обновить список пресетов
        self._load_presets_list()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Убираем белое мигание — устанавливаем тёмный фон до показа окна
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#111827"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Инициализация переводчика
        self.translator = Translator.get_instance()
        detected_lang = detect_locale()
        self.translator.set_language(detected_lang)
        self.current_language = detected_lang
        
        self.setWindowTitle(self.tr("FFmpeg Converter"))
        self.setWindowIcon(QIcon(get_window_icon_path()))
        self.resize(1100, 750)
        self.setMinimumSize(850, 600)
        
        # Центрирование на текущем мониторе
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        
        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()
        
        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None
        self.worker = None
        self.installer = None
        
        self._init_ui()
        self._check_ffmpeg()
    
    def tr(self, text: str) -> str:
        """Translate text to current language."""
        return self.translator.tr(text)
    
    def _init_ui(self):
        # Центральное окно
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(self.tr("FFmpeg Converter"))
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        # Language switcher — QToolButton + QMenu
        self.lang_button = QToolButton()
        self.lang_button.setFixedHeight(36)
        self.lang_button.setFixedWidth(76)
        self.lang_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.lang_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_button.setAccessibleName(self.tr("Language selector"))
        self.lang_button.setToolTip(self.tr("Выберите язык интерфейса / Select language"))
        self._update_lang_button_text()
        
        self.lang_button.setStyleSheet("""
            QToolButton {
                background-color: #374151;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: "Segoe UI";
            }
            QToolButton:hover {
                background-color: #4b5563;
                border-color: #6b7280;
            }
            QToolButton:focus {
                border-color: #2563eb;
                outline: none;
            }
            QToolButton:pressed {
                background-color: #4b5563;
                border-color: #2563eb;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0;
            }
        """)
        
        # Menu
        self.lang_menu = QMenu(self.lang_button)
        self.lang_menu.setStyleSheet("""
            QMenu {
                background-color: #1f2937;
                color: #f9fafb;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 6px;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #374151;
            }
            QMenu::item:checked {
                background-color: #2563eb;
                font-weight: bold;
            }
        """)
        
        self.lang_actions = {}
        for code, name in [("ru", "Русский"), ("en", "English")]:
            action = QAction(name, self.lang_menu)
            action.setCheckable(True)
            action.setChecked(code == self.current_language)
            action.triggered.connect(lambda checked, c=code: self._change_language(c))
            self.lang_menu.addAction(action)
            self.lang_actions[code] = action
        
        self.lang_button.setMenu(self.lang_menu)
        
        header.addWidget(self.lang_button)
        
        self.ffmpeg_status_label = QLabel(self.tr("Проверка..."))
        self.ffmpeg_status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.ffmpeg_status_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ffmpeg_status_label.mousePressEvent = self._on_ffmpeg_status_click
        header.addWidget(self.ffmpeg_status_label)
        
        layout.addLayout(header)
        
        # Баннер установки с современным дизайном
        self.install_banner = QFrame()
        self.install_banner.setObjectName("installBanner")
        self.install_banner.setFixedHeight(70)
        self.install_banner.setStyleSheet("""
            QFrame#installBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #d97706, stop:1 #b45309);
                border-radius: 8px;
                padding: 5px;
            }
        """)
        self.install_banner.hide()
        
        banner_layout = QHBoxLayout(self.install_banner)
        banner_layout.setContentsMargins(20, 10, 20, 10)
        banner_layout.setSpacing(15)
        
        # Иконка состояния
        self.install_banner_icon = QLabel("⚠️")
        self.install_banner_icon.setStyleSheet("font-size: 28px; padding: 5px; background: transparent;")
        banner_layout.addWidget(self.install_banner_icon)
        
        # Текстовый блок (заголовок + описание)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.install_banner_title = QLabel(self.tr("FFmpeg не найден"))
        self.install_banner_title.setStyleSheet("""
            color: white; 
            font-size: 14px; 
            font-weight: bold;
            font-family: "Segoe UI";
            background: transparent;
            border: none;
        """)
        text_layout.addWidget(self.install_banner_title)
        
        self.install_banner_desc = QLabel(self.tr("Установите FFmpeg для работы конвертера"))
        self.install_banner_desc.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85); 
            font-size: 12px;
            font-family: "Segoe UI";
            background: transparent;
            border: none;
        """)
        text_layout.addWidget(self.install_banner_desc)
        
        banner_layout.addLayout(text_layout)
        banner_layout.addStretch()
        
        # Прогресс-бар (на всю ширину баннера)
        self.install_progress = QProgressBar()
        self.install_progress.setRange(0, 100)
        self.install_progress.setValue(0)
        self.install_progress.setFixedHeight(8)
        self.install_progress.setTextVisible(False)
        self.install_progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: white;
                border-radius: 4px;
            }
        """)
        self.install_progress.hide()
        banner_layout.addWidget(self.install_progress)
        
        # Кнопка установки
        self.install_btn = QPushButton(self.tr("Установить"))
        self.install_btn.setFixedHeight(36)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #d97706;
                font-size: 13px;
                font-weight: bold;
                font-family: "Segoe UI";
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #f9fafb;
            }
            QPushButton:pressed {
                background-color: #e5e7eb;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.5);
                color: rgba(0, 0, 0, 0.3);
            }
        """)
        self.install_btn.clicked.connect(self._install_ffmpeg)
        banner_layout.addWidget(self.install_btn)
        
        layout.addWidget(self.install_banner)
        
        # Баннер обновления
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("background-color: #0284c7; padding: 10px;")
        self.update_banner.hide()
        
        update_layout = QHBoxLayout(self.update_banner)
        self.update_label = QLabel(self.tr("🔄 Доступна новая версия FFmpeg"))
        self.update_label.setStyleSheet("color: white; font-weight: bold;")
        update_layout.addWidget(self.update_label)
        
        update_btn = QPushButton(self.tr("Обновить"))
        update_btn.setStyleSheet("QPushButton { background-color: #15803d; color: white; padding: 8px 15px; border-radius: 4px; }")
        update_btn.clicked.connect(self._show_update_dialog)
        update_layout.addWidget(update_btn)
        
        dismiss_btn = QPushButton(self.tr("✕"))
        dismiss_btn.setStyleSheet("QPushButton { background: transparent; border: 1px solid white; color: white; padding: 5px 10px; border-radius: 3px; } QPushButton:hover { background-color: #dc2626; }")
        dismiss_btn.clicked.connect(self.update_banner.hide)
        update_layout.addWidget(dismiss_btn)
        update_layout.addStretch()
        
        layout.addWidget(self.update_banner)
        
        # Выбор папки
        self.folder_group = QGroupBox(self.tr("Папка с файлами"))
        folder_layout = QHBoxLayout(self.folder_group)
        
        self.select_folder_btn = QPushButton(self.tr("📁 Выбрать папку"))
        self.select_folder_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.select_folder_btn)
        
        self.refresh_btn = QPushButton(self.tr("🔄 Обновить"))
        self.refresh_btn.clicked.connect(self._refresh_files)
        self.refresh_btn.setMaximumWidth(150)
        folder_layout.addWidget(self.refresh_btn)
        
        self.folder_label = QLabel(self.tr("Папка не выбрана"))
        self.folder_label.setStyleSheet("color: #6b7280;")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch()
        
        layout.addWidget(self.folder_group)
        
        # Пресеты
        self.preset_group = QGroupBox(self.tr("Настройки конвертации"))
        preset_layout = QVBoxLayout(self.preset_group)
        
        # Первая строка: комбобокс + кнопка
        top_row = QHBoxLayout()
        self.preset_label = QLabel(self.tr("Пресет:"))
        top_row.addWidget(self.preset_label, 0, Qt.AlignmentFlag.AlignRight)
        
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        self.preset_combo.setObjectName("preset_combo")
        
        # Добавляем пресеты с ID в userData для корректного поиска
        for preset in self.preset_manager.get_all_presets():
            preset_name_key = f"preset.{preset.id}.name"
            localized_name = self.tr(preset_name_key)
            if localized_name == preset_name_key:
                localized_name = preset.name
            self.preset_combo.addItem(localized_name, preset.id)
        
        top_row.addWidget(self.preset_combo, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.builder_btn = QPushButton(self.tr("🛠 Конструктор"))
        self.builder_btn.clicked.connect(self._open_preset_builder)
        top_row.addWidget(self.builder_btn)
        top_row.addStretch()
        
        preset_layout.addLayout(top_row)
        
        # Вторая строка: описание пресета
        self.preset_info = QLabel("")
        self.preset_info.setStyleSheet("color: #6b7280; font-style: italic; font-size: 11px;")
        self.preset_info.setWordWrap(True)
        preset_layout.addWidget(self.preset_info)
        
        # Подключаем сигнал ПОСЛЕ создания всех виджетов
        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        
        # Автоматически выбираем первый пресет
        if self.preset_combo.count() > 0:
            self.preset_combo.setCurrentIndex(0)
            self._preset_changed(self.preset_combo.itemText(0))
        
        layout.addWidget(self.preset_group)
        
        # Список файлов
        self.files_group = QGroupBox(self.tr("Файлы"))
        files_layout = QVBoxLayout(self.files_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setSpacing(2)
        self.files_layout.addStretch()
        
        scroll.setWidget(self.files_container)
        files_layout.addWidget(scroll)
        
        self.files_count = QLabel(self.tr("Файлов: 0/0"))
        self.files_count.setStyleSheet("color: #6b7280;")
        
        # Кнопки управления выделением
        select_btns = QHBoxLayout()
        select_btns.addWidget(self.files_count)
        select_btns.addStretch()
        
        self.select_all_btn = QPushButton(self.tr("✓ Все"))
        self.select_all_btn.setMaximumWidth(80)
        self.select_all_btn.clicked.connect(self._select_all_files)
        select_btns.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton(self.tr("✗ Все"))
        self.deselect_all_btn.setMaximumWidth(80)
        self.deselect_all_btn.clicked.connect(self._deselect_all_files)
        select_btns.addWidget(self.deselect_all_btn)
        
        files_layout.addLayout(select_btns)
        
        layout.addWidget(self.files_group)
        
        # Прогресс
        self.progress_group = QGroupBox(self.tr("Конвертация"))
        progress_layout = QHBoxLayout(self.progress_group)
        
        self.convert_btn = QPushButton(self.tr("▶ Конвертировать"))
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet("QPushButton { background-color: #2563eb; color: white; font-size: 13px; font-weight: bold; border-radius: 4px; padding: 10px; } QPushButton:hover { background-color: #1d4ed8; } QPushButton:disabled { background-color: #4b5563; }")
        self.convert_btn.clicked.connect(self._convert)
        progress_layout.addWidget(self.convert_btn)
        
        self.cancel_btn = QPushButton(self.tr("⏹ Стоп"))
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #dc2626; color: white; font-size: 13px; font-weight: bold; border-radius: 4px; padding: 10px; } QPushButton:hover { background-color: #b91c1c; } QPushButton:disabled { background-color: #4b5563; }")
        self.cancel_btn.clicked.connect(self._cancel_conversion)
        self.cancel_btn.setEnabled(False)
        progress_layout.addWidget(self.cancel_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(35)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setMinimumWidth(200)
        self.progress_label.setStyleSheet("color: #6b7280;")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(self.progress_group)
        
        # Лог
        self.log_group = QGroupBox(self.tr("Лог операций"))
        log_layout = QVBoxLayout(self.log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        log_layout.addWidget(self.log_text)
        
        self.log_group.setMaximumHeight(120)
        self.log_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.log_group)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.convert_status_label = QLabel("")
        self.convert_status_label.setStyleSheet("font-size: 12px;")
        self.status_bar.addWidget(self.convert_status_label)
    
    def _change_language(self, lang_code: str):
        """Мгновенное переключение языка по коду (ru/en)."""
        try:
            if lang_code not in ("ru", "en"):
                return
            self.current_language = lang_code
            self.translator.set_language(self.current_language)
            
            # Обновить checkmarks в меню
            for code, action in self.lang_actions.items():
                action.setChecked(code == self.current_language)
            
            # Обновить текст кнопки
            self._update_lang_button_text()
            
            # Обновить все тексты UI
            self._update_ui_text()
            
            # Feedback
            lang_name = "English" if self.current_language == "en" else "Русский"
            msg = self.tr("Language changed to English") if self.current_language == "en" else self.tr("Язык изменён на Русский")
            self.status_bar.showMessage(msg, 2000)
        except Exception as e:
            print(f"ERROR in _change_language: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_lang_button_text(self):
        """Обновить текст кнопки языка."""
        code = self.current_language.upper()
        if hasattr(self, 'lang_button'):
            self.lang_button.setText(f"🌐 {code}")
    
    def _update_ui_text(self):
        """Обновить все тексты UI при переключении языка."""
        # Header
        self.setWindowTitle(self.tr("FFmpeg Converter"))
        
        # FFmpeg status
        if hasattr(self, 'ffmpeg_available'):
            if self.ffmpeg_available:
                version = getattr(self, 'ffmpeg_version', '?')
                self.ffmpeg_status_label.setText(self.tr("✓ FFmpeg {version}").replace("{version}", version))
            else:
                self.ffmpeg_status_label.setText(self.tr("✗ FFmpeg не найден"))
        else:
            self.ffmpeg_status_label.setText(self.tr("Проверка..."))
        
        # Install banner
        if hasattr(self, 'install_banner_title'):
            self.install_banner_title.setText(self.tr("FFmpeg не найден"))
        if hasattr(self, 'install_banner_desc'):
            self.install_banner_desc.setText(self.tr("Установите FFmpeg для работы конвертера"))
        if hasattr(self, 'install_btn'):
            self.install_btn.setText(self.tr("Установить"))
        
        # Groups
        if hasattr(self, 'folder_group'):
            self.folder_group.setTitle(self.tr("Папка с файлами"))
        if hasattr(self, 'preset_group'):
            self.preset_group.setTitle(self.tr("Настройки конвертации"))
        if hasattr(self, 'files_group'):
            self.files_group.setTitle(self.tr("Файлы"))
        if hasattr(self, 'progress_group'):
            self.progress_group.setTitle(self.tr("Конвертация"))
        if hasattr(self, 'log_group'):
            self.log_group.setTitle(self.tr("Лог операций"))
        
        # Buttons
        if hasattr(self, 'select_folder_btn'):
            self.select_folder_btn.setText(self.tr("📁 Выбрать папку"))
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setText(self.tr("🔄 Обновить"))
        if hasattr(self, 'builder_btn'):
            self.builder_btn.setText(self.tr("🛠 Конструктор"))
        if hasattr(self, 'select_all_btn'):
            self.select_all_btn.setText(self.tr("✓ Все"))
        if hasattr(self, 'deselect_all_btn'):
            self.deselect_all_btn.setText(self.tr("✗ Все"))
        if hasattr(self, 'convert_btn'):
            self.convert_btn.setText(self.tr("▶ Конвертировать"))
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setText(self.tr("⏹ Стоп"))
        
        # Labels
        if hasattr(self, 'folder_label'):
            if self.selected_folder:
                self.folder_label.setText(str(self.selected_folder))
            else:
                self.folder_label.setText(self.tr("Папка не выбрана"))
        
        if hasattr(self, 'files_count'):
            total = len(self.files_list)
            selected = sum(1 for f in self.files_list if f['checkbox'].isChecked())
            self.files_count.setText(self.tr("Файлов: {selected}/{total}").format(selected=selected, total=total))
        
        # Update language button
        if hasattr(self, 'lang_actions'):
            for code, action in self.lang_actions.items():
                action.setChecked(code == self.current_language)
        if hasattr(self, 'lang_button'):
            self._update_lang_button_text()
        
        # Update preset combo box with localized names
        if hasattr(self, 'preset_combo') and hasattr(self, 'preset_manager'):
            self.preset_combo.blockSignals(True)
            current_id = self.preset_combo.itemData(self.preset_combo.currentIndex(), Qt.ItemDataRole.UserRole)
            self.preset_combo.clear()
            
            # Добавляем локализованные названия пресетов с ID
            for preset in self.preset_manager.get_all_presets():
                preset_name_key = f"preset.{preset.id}.name"
                localized_name = self.tr(preset_name_key)
                if localized_name == preset_name_key:
                    localized_name = preset.name
                self.preset_combo.addItem(localized_name, preset.id)
            
            # Восстанавливаем текущий выбор по ID
            restored = False
            if current_id:
                for i in range(self.preset_combo.count()):
                    if self.preset_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_id:
                        self.preset_combo.setCurrentIndex(i)
                        restored = True
                        break
            if not restored and self.preset_combo.count() > 0:
                self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)
            
            # Обновляем описание пресета после восстановления выбора
            if self.preset_combo.count() > 0:
                self._preset_changed("")
        
        # Update preset label
        if hasattr(self, 'preset_label'):
            self.preset_label.setText(self.tr("Пресет:"))
    
    def _check_ffmpeg(self):
        """Проверка наличия FFmpeg с использованием PlatformManager."""
        # Получаем платформу
        platform = PlatformManager.get_platform()
        
        # Проверяем в PATH
        self.ffmpeg_available = shutil.which("ffmpeg") is not None
        
        # Проверяем в директории установки
        install_dir = platform.get_ffmpeg_install_path()
        ffmpeg_exe = install_dir / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if ffmpeg_exe.exists():
            self.ffmpeg_available = True
        
        if self.ffmpeg_available:
            self.ffmpeg_version = FFmpegInstaller.get_ffmpeg_version()
            self.ffmpeg_status_label.setText(f"✓ FFmpeg {self.ffmpeg_version}")
            self.ffmpeg_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            self.ffmpeg_status_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.install_banner.hide()
            QTimer.singleShot(8000, self._check_updates)
        else:
            self.ffmpeg_status_label.setText(self.tr("✗ FFmpeg не найден"))
            self.ffmpeg_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            # После удаления показываем баннер
            self.install_banner.show()
            # Сбрасываем прогресс и кнопку
            self.install_progress.hide()
            self.install_progress.setValue(0)
            self.install_btn.setText(self.tr("Установить"))
            self.install_banner_icon.setText("⚠️")
            self.install_banner_title.setText(self.tr("FFmpeg не найден"))
            self.install_banner_desc.setText(self.tr("Установите FFmpeg для работы конвертера"))
    
    def _check_updates(self):
        """Проверить обновления и показать информацию"""
        try:
            update_info = FFmpegUpdater.get_update_info()
            if update_info:
                # Показываем версию в баннере
                self.update_label.setText(
                    self.tr("🔄 Доступна версия {version} (у вас {current})").format(
                        version=update_info['version'],
                        current=self.ffmpeg_version
                    )
                )
                self.update_banner.show()
        except Exception as e:
            print(f"Update check error: {e}")
    
    def _open_preset_builder(self):
        """Открыть конструктор пресетов"""
        dlg = PresetBuilderDialog(self, self.preset_manager)
        self.translator._signal.connect(dlg._update_ui_text)
        dlg.finished.connect(lambda: self.translator._signal.disconnect(dlg._update_ui_text))
        dlg.show()
    
    def _on_ffmpeg_status_click(self, event):
        """Обработка клика на статус FFmpeg — показать меню"""
        if not self.ffmpeg_available:
            return
        
        platform = PlatformManager.get_platform()
        install_dir = platform.get_ffmpeg_install_path()
        
        menu = QMenu(self)
        menu.addAction(self.tr("✓ FFmpeg {version}").replace("{version}", self.ffmpeg_version))
        menu.addSeparator()
        menu.addAction(self.tr("📁 Открыть папку"), lambda: platform.open_file_explorer(install_dir))
        menu.addAction(self.tr("🗑️ Удалить FFmpeg"), self._uninstall_ffmpeg)
        
        # Добавляем разделитель и пункт удаления программы
        menu.addSeparator()
        menu.addAction(self.tr("❌ Удалить программу"), self._uninstall_program)
        
        # Показываем меню в позиции клика
        menu.exec(self.ffmpeg_status_label.mapToGlobal(event.pos()))
    
    def _uninstall_ffmpeg(self):
        """Удалить FFmpeg"""
        # Сначала удаляем ярлык с рабочего стола
        desktop_shortcut = Path.home() / "Desktop" / "Удалить FFmpeg.lnk"
        if desktop_shortcut.exists():
            try:
                desktop_shortcut.unlink()
                self._log(self.tr("✓ Ярлык удаления удалён"))
            except Exception as e:
                self._log(self.tr("⚠️ Не удалось удалить ярлык: {error}").replace("{error}", str(e)))
        
        # Удаляем FFmpeg через Python
        if FFmpegInstaller.uninstall():
            self._log(self.tr("✓ FFmpeg удалён"))
            self._check_ffmpeg()
        else:
            self.convert_status_label.setText(self.tr("✗ Ошибка удаления"))
            self.convert_status_label.setStyleSheet("color: #ef4444;")
    
    def _uninstall_program(self):
        """Запустить деинсталлятор программы"""
        try:
            from src.uninstall import UninstallDialog
            dlg = UninstallDialog(self.translator)
            dlg.exec()
        except ImportError:
            # Fallback: запуск через subprocess
            import subprocess
            uninstall_path = Path(__file__).parent / "uninstall.py"
            if uninstall_path.exists():
                subprocess.run([sys.executable, str(uninstall_path), self.current_language])
            else:
                self.convert_status_label.setText(self.tr("⚠️ Деинсталлятор не найден"))
                self.convert_status_label.setStyleSheet("color: #f59e0b;")
    
    def _show_update_dialog(self):
        """Показать диалог обновления FFmpeg"""
        # Получаем информацию об обновлении
        update_info = FFmpegUpdater.get_update_info()
        
        if not update_info:
            self.convert_status_label.setText(self.tr("⚠️ Не удалось проверить обновления"))
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
            return
        
        # Создаём диалог
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Обновление FFmpeg"))
        dlg.setMinimumWidth(450)
        dlg.setModal(True)
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel(self.tr("🔄 Доступна новая версия"))
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Информация о версии
        info = QLabel(
            f"<b>{self.tr('Текущая версия:')}</b> {self.ffmpeg_version}<br>"
            f"<b>{self.tr('Новая версия:')}</b> {update_info['version']}<br>"
            f"<b>{self.tr('Дата выпуска:')}</b> {update_info['date'][:10]}"
        )
        info.setStyleSheet("font-size: 13px; padding: 10px; background: #1f2937; border-radius: 5px;")
        layout.addWidget(info)
        
        # Описание
        desc = QLabel(
            self.tr("Обновление загрузит и установит новую версию FFmpeg.\n"
            "Старая версия будет заменена.\n"
            "Пользовательские пресеты сохранятся.")
        )
        desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(desc)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton(self.tr("Отмена"))
        cancel_btn.setStyleSheet("QPushButton { background: transparent; border: 1px solid #4b5563; padding: 8px 20px; border-radius: 4px; }")
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addWidget(cancel_btn)
        
        update_btn = QPushButton(self.tr("Обновить"))
        update_btn.setStyleSheet("QPushButton { background-color: #15803d; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }")
        update_btn.clicked.connect(lambda: [dlg.accept(), self._install_ffmpeg()])
        btn_layout.addWidget(update_btn)
        
        layout.addLayout(btn_layout)
        
        dlg.exec()
    
    def _install_ffmpeg(self):
        """Начать установку FFmpeg"""
        if self.installer and self.installer.isRunning():
            return
        
        # Скрываем баннер обновления
        self.update_banner.hide()
        
        # Блокируем кнопку и показываем прогресс
        self.install_btn.setEnabled(False)
        self.install_btn.setText(self.tr("Установка..."))
        self.install_progress.show()
        self.install_progress.setValue(0)
        
        # Запускаем установку
        self.installer = InstallerThread()
        self.installer.progress.connect(self._update_install_progress)
        self.installer.finished.connect(self._install_done)
        self.installer.start()
    
    def _update_install_progress(self, value: int):
        """Обновление прогресс-бара установки"""
        self.install_progress.setValue(value)
        self.install_banner_title.setText(self.tr("Загрузка FFmpeg..."))
        self.install_banner_desc.setText(self.tr("Пожалуйста, дождитесь завершения ({value}%)").format(value=value))
        self.status_bar.showMessage(self.tr("Установка... {value}%").format(value=value), 2000)
    
    def _install_done(self, ok: bool):
        """Завершение установки FFmpeg — безопасно для потока"""
        # Сохраняем значения в атрибуты объекта ПЕРЕД планированием
        self._install_result_ok = ok
        
        # Проверяем что окно ещё существует и не скрыто
        if self.isHidden() or not self.isVisible():
            return
        
        # Планируем вызов в главном потоке
        QTimer.singleShot(0, self._finish_install_safe)
    
    def _finish_install_safe(self):
        """Безопасное завершение установки (вызывается в главном потоке)"""
        try:
            ok = getattr(self, '_install_result_ok', False)
            
            if not ok:
                self._log(self.tr("✗ Ошибка установки FFmpeg"))
                self.convert_status_label.setText(self.tr("✗ Ошибка установки FFmpeg"))
                self.convert_status_label.setStyleSheet("color: #ef4444;")
                
                # Возвращаем баннер в исходное состояние
                self.install_btn.setEnabled(True)
                self.install_btn.setText(self.tr("Установить"))
                self.install_progress.hide()
                self.install_progress.setValue(0)
                self.install_banner_icon.setText("⚠️")
                self.install_banner_title.setText(self.tr("FFmpeg не найден"))
                self.install_banner_desc.setText(self.tr("Установите FFmpeg для работы конвертера"))
                return
            
            # Небольшая задержка чтобы FFmpeg успел записаться на диск
            import time
            time.sleep(0.5)
            
            self._check_ffmpeg()
            version = FFmpegInstaller.get_ffmpeg_version()
            self._log(self.tr("✓ FFmpeg установлен: {version}").replace("{version}", version))
            
            # Создаём деинсталлятор и ярлык
            self._create_uninstaller()
            self._create_uninstall_shortcut()
            
            # Скрываем баннер установки
            self.install_banner.hide()
            self.install_progress.hide()
            self.install_progress.setValue(0)
            
            # Очищаем ссылку на установщик
            self.installer = None
            
        except Exception as e:
            print(f"ERROR in _finish_install_safe: {e}")
            import traceback
            traceback.print_exc()
            self._log(self.tr("✗ Ошибка после установки: {error}").replace("{error}", str(e)))
    
    def _create_uninstaller(self):
        """Создать BAT-файл для удаления FFmpeg в папке FFmpegGUI"""
        try:
            uninstall_dir = Path.home() / "FFmpegGUI"
            uninstall_dir.mkdir(parents=True, exist_ok=True)
            bat_path = uninstall_dir / "Uninstall_FFmpeg.bat"
            
            # BAT-файл удаляет всю папку FFmpegGUI (включая себя)
            bat_content = r'''@echo off
echo.
echo ====================================
echo  FFmpeg Uninstaller
echo ====================================
echo.

echo [1/4] Завершение процессов FFmpeg...
taskkill /F /IM ffmpeg.exe 2>nul
taskkill /F /IM ffprobe.exe 2>nul
taskkill /F /IM ffplay.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Удаляю ярлык с рабочего стола...
del /q "%USERPROFILE%\Desktop\Удалить FFmpeg.lnk" 2>nul

echo [3/4] Удаляю папку FFmpegGUI...
rmdir /s /q "%USERPROFILE%\FFmpegGUI" 2>nul
if exist "%USERPROFILE%\FFmpegGUI" (
    echo [ERROR] Не удалось удалить папку FFmpegGUI
    echo [ERROR] Закройте все программы и попробуйте снова
    pause
    exit /b 1
)

echo [4/4] Готово!
echo.
echo ====================================
echo  FFmpegGUI полностью удалён.
echo  Освобождено: ~600 MB
echo ====================================
echo.

timeout /t 3 /nobreak >nul
exit
'''
            bat_path.write_text(bat_content, encoding='cp866')
            
        except Exception as e:
            print(f"ERROR creating uninstaller: {e}")
    
    def _create_uninstall_shortcut(self):
        """Создать ярлык удаления FFmpeg на рабочем столе"""
        try:
            # Рабочий стол
            desktop = Path.home() / "Desktop"
            shortcut_name = "Удалить FFmpeg.lnk"
            shortcut_path = desktop / shortcut_name
            
            # Ярлык на Uninstall_FFmpeg.bat
            bat_path = Path.home() / "FFmpegGUI" / "Uninstall_FFmpeg.bat"
            
            # Создаём ярлык через WScript
            import subprocess
            vbs_script = f'''
Set WshShell = CreateObject("WScript.Shell")
Set oLink = WshShell.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{bat_path}"
oLink.WorkingDirectory = "{bat_path.parent}"
oLink.Description = "Удалить FFmpegGUI (600 MB)"
oLink.IconLocation = "shell32.dll,161"
oLink.Save
'''
            vbs_path = Path(tempfile.gettempdir()) / "create_shortcut.vbs"
            vbs_path.write_text(vbs_script)
            
            result = subprocess.run(["cscript", "//nologo", str(vbs_path)], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status_bar.showMessage(self.tr("✓ Ярлык удаления создан на рабочем столе"), 5000)
            else:
                print(f"CScript error: {result.stderr}")
            
        except Exception as e:
            print(f"ERROR creating shortcut: {e}")
            import traceback
            traceback.print_exc()
    
    def _select_folder(self):
        # По умолчанию открываем папку пользователя
        default_dir = str(Path.home())
        
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Папка с файлами"),
            default_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(folder)
            self.files_list = []
            
            # Очистка
            while self.files_layout.count() > 1:
                item = self.files_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            
            exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            
            video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            
            # Исключаем папку output из конвертации
            output_folder_name = "output"
            
            for f in Path(folder).iterdir():
                # Пропускаем папки и папку output
                if not f.is_file():
                    continue
                if f.name == output_folder_name and f.parent == folder:
                    continue
                
                suffix = f.suffix.lower()
                name_lower = f.name.lower()
                
                # Проверяем: точное расширение ИЛИ вхождение в имя
                is_video = suffix in exts or any(ext in name_lower for ext in video_exts)
                is_image = suffix in exts or any(ext in name_lower for ext in image_exts)
                
                if is_video or is_image:
                        # Создаём строку с чекбоксом
                        row = QFrame()
                        row.setStyleSheet("background: #1f2937; border-radius: 3px;")
                        row_layout = QHBoxLayout(row)
                        row_layout.setContentsMargins(10, 5, 10, 5)
                        row_layout.setSpacing(10)
                        
                        checkbox = QCheckBox()
                        checkbox.setChecked(True)  # Выбран по умолчанию
                        checkbox.stateChanged.connect(self._update_files_count)
                        row_layout.addWidget(checkbox)
                        
                        label = QLabel(f"{f.name}  —  {f.stat().st_size / (1024**3):.2f} GB")
                        label.setStyleSheet("padding: 4px;")
                        row_layout.addWidget(label, 1)  # Растягивается
                        
                        row_layout.addStretch()
                        
                        self.files_layout.insertWidget(self.files_layout.count() - 1, row)
                        
                        # Сохраняем путь и чекбокс
                        self.files_list.append({"path": str(f), "checkbox": checkbox, "widget": row})
            
            self._update_files_count()
    
    def _update_files_count(self):
        """Обновить счётчик файлов"""
        selected = sum(1 for f in self.files_list if f["checkbox"].isChecked())
        total = len(self.files_list)
        self.files_count.setText(self.tr("Файлов: {selected}/{total}").format(selected=selected, total=total))
    
    def _refresh_files(self):
        """Обновить список файлов в текущей папке"""
        if not self.selected_folder:
            self.status_bar.showMessage(self.tr("⚠️ Сначала выберите папку"), 3000)
            return
        
        # Очищаем текущий список
        while self.files_layout.count() > 1:
            item = self.files_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        self.files_list = []
        
        # Загружаем файлы заново
        exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        
        video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        
        for f in Path(self.selected_folder).iterdir():
            if f.is_file():
                suffix = f.suffix.lower()
                name_lower = f.name.lower()
                
                is_video = suffix in exts or any(ext in name_lower for ext in video_exts)
                is_image = suffix in exts or any(ext in name_lower for ext in image_exts)
                
                if is_video or is_image:
                    # Создаём строку с чекбоксом
                    row = QFrame()
                    row.setStyleSheet("background: #1f2937; border-radius: 3px;")
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(10, 5, 10, 5)
                    row_layout.setSpacing(10)
                    
                    checkbox = QCheckBox()
                    checkbox.setChecked(True)  # Выбран по умолчанию
                    checkbox.stateChanged.connect(self._update_files_count)
                    row_layout.addWidget(checkbox)
                    
                    label = QLabel(f"{f.name}  —  {f.stat().st_size / (1024**3):.2f} GB")
                    label.setStyleSheet("padding: 4px;")
                    row_layout.addWidget(label, 1)  # Растягивается
                    
                    row_layout.addStretch()
                    
                    self.files_layout.insertWidget(self.files_layout.count() - 1, row)
                    
                    # Сохраняем путь и чекбокс
                    self.files_list.append({"path": str(f), "checkbox": checkbox, "widget": row})
        
        self._update_files_count()
        self.status_bar.showMessage("✓ Список файлов обновлён", 3000)
    
    def _select_all_files(self):
        """Выбрать все файлы"""
        for f in self.files_list:
            f["checkbox"].setChecked(True)
    
    def _deselect_all_files(self):
        """Снять выделение со всех файлов"""
        for f in self.files_list:
            f["checkbox"].setChecked(False)
    
    def _get_selected_files(self):
        """Получить список выбранных файлов"""
        return [f["path"] for f in self.files_list if f["checkbox"].isChecked()]
    
    def _preset_changed(self, name):
        """Handle preset selection change using stored preset ID."""
        # Получаем ID пресета из userData текущего элемента
        current_index = self.preset_combo.currentIndex()
        if current_index < 0:
            return
        
        preset_id = self.preset_combo.itemData(current_index, Qt.ItemDataRole.UserRole)
        if not preset_id:
            return
        
        p = self.preset_manager.get_preset(preset_id)
        if p:
            self.selected_preset = p
            # Используем перевод описания пресета по ключу
            preset_description_key = f"preset.{p.id}.description"
            translated_description = self.tr(preset_description_key)
            # Если перевод не найден, используем оригинальное описание
            if translated_description == preset_description_key:
                translated_description = p.description
            self.preset_info.setText(translated_description)
    
    def _convert(self):
        if not self.ffmpeg_available:
            self.convert_status_label.setText("✗ FFmpeg не найден")
            self.convert_status_label.setStyleSheet("color: #ef4444;")
            return
        
        # Получаем выбранные файлы
        selected_files = self._get_selected_files()
        
        if not selected_files:
            self.convert_status_label.setText("⚠️ Выберите файлы")
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
            return
        
        if not self.selected_preset:
            self.convert_status_label.setText(self.tr("⚠️ Нет пресета"))
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
            return
        
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected_files))
        self.convert_status_label.setText(self.tr("Конвертация..."))
        self.convert_status_label.setStyleSheet("color: #f59e0b;")
        
        out = Path(self.selected_folder) / "output"
        out.mkdir(exist_ok=True)
        
        self.worker = WorkerThread(selected_files, out, self.selected_preset, self.ffmpeg, self.translator)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_done)
        self.worker.log.connect(self._log)
        self.worker.start()
    
    def _cancel_conversion(self):
        """Отмена конвертации"""
        if self.worker and self.worker.isRunning():
            self.worker.kill()  # Мгновенное завершение ffmpeg.exe
            self.convert_status_label.setText(self.tr("⚠️ Отмена..."))
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
    
    def _on_progress(self, current, name):
        """Обновление прогресса"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(name)
    
    def _on_done(self, success, ok, err):
        """Завершение конвертации"""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        total = ok + err
        
        if err == 0:
            # Всё успешно
            self.convert_status_label.setText(self.tr("✓ Успешно: {ok} из {total}").format(ok=ok, total=total))
            self.convert_status_label.setStyleSheet("color: #22c55e;")
        elif ok == 0:
            # Все файлы с ошибкой
            self.convert_status_label.setText(self.tr("✗ Ошибка: 0 из {total}").format(total=total))
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
        else:
            # Частичный успех
            self.convert_status_label.setText(self.tr("⚠️ Успешно: {ok} из {total}, ошибок: {err}").format(ok=ok, total=total, err=err))
            self.convert_status_label.setStyleSheet("color: #f59e0b;")
        
        # Очистка статуса через 30 секунд
        QTimer.singleShot(30000, lambda: self.convert_status_label.setText(""))
    
    def _log(self, msg):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {msg}")


def main():
    """Точка входа приложения"""
    # Настройка DPI
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            pass
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Тёмная тема
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #111827;
            color: #f9fafb;
            font-family: "Segoe UI";
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #374151;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QComboBox, QLineEdit, QTextEdit {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 6px;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QScrollBar:vertical {
            background: #1f2937;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #4b5563;
            border-radius: 5px;
        }
        QProgressBar {
            background: #1f2937;
            border: none;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #2563eb;
            border-radius: 4px;
        }
        QListWidget {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 5px;
        }
        QListWidget::item {
            padding: 5px;
            border-radius: 3px;
        }
        QListWidget::item:selected {
            background-color: #2563eb;
        }
        QListWidget::item:hover {
            background-color: #374151;
        }
    """)
    
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
