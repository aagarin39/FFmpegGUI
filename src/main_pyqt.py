"""
FFmpeg Converter - PyQt6 версия
Стабильный интерфейс без дерганий на многомониторных системах
"""
import sys
import os
import shutil
import subprocess
import threading
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFileDialog,
    QScrollArea, QFrame, QMessageBox, QGroupBox, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QMenu, QStatusBar, QDialog,
    QSlider, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QAction

# Импорт модулей проекта
if getattr(sys, 'frozen', False):
    import src.core.ffmpeg
    import src.core.ffmpeg_installer
    import src.core.ffmpeg_updater
    import src.core.presets
    from src.platform import PlatformManager
    from src.core.config import get_config
    
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
    PresetManager = src.core.presets.PresetManager
    Preset = src.core.presets.Preset
    FFmpegInstaller = src.core.ffmpeg_installer.FFmpegInstaller
    FFmpegUpdater = src.core.ffmpeg_updater.FFmpegUpdater
else:
    try:
        from .core.ffmpeg import FFmpegWrapper
        from .core.ffmpeg_installer import FFmpegInstaller
        from .core.ffmpeg_updater import FFmpegUpdater
        from .core.presets import PresetManager, Preset
        from .platform import PlatformManager
        from .core.config import get_config
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.ffmpeg_installer import FFmpegInstaller
        from core.ffmpeg_updater import FFmpegUpdater
        from core.presets import PresetManager, Preset
        from platform import PlatformManager
        from core.config import get_config


class WorkerThread(QThread):
    """Поток для фоновых задач"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, int, int)
    log = pyqtSignal(str)
    
    def __init__(self, files, output_folder, preset, ffmpeg):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.preset = preset
        self.ffmpeg = ffmpeg
        self.process = None  # Ссылка на subprocess.Popen
        self._cancel_flag = False
    
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
                self.log.emit("⚠️ Конвертация отменена пользователем")
                break
            
            name = Path(file).name
            self.log.emit(f"▶ {name}")
            
            ext = self.preset.container if self.preset.container else "mkv"
            output = str(self.output_folder / f"{Path(file).stem}.{ext}")
            
            try:
                if self.ffmpeg.convert(file, output, self.preset, self):
                    ok += 1
                    self.log.emit(f"✓ {name}")
                else:
                    if self._cancel_flag:
                        break
                    err += 1
                    self.log.emit(f"✗ {name}")
            except Exception as e:
                err += 1
                self.log.emit(f"✗ {name}: {e}")
            
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
    
    HELP_TEXTS = {
        "name": "Уникальное название пресета (например: 'Для телефона', 'YouTube 1080p')",
        "desc": "Краткое описание для быстрого понимания назначения пресета",
        "hw": "Аппаратное ускорение кодирует видео быстрее:\n• nvenc — видеокарты NVIDIA (рекомендуется)\n• qsv — встроенная графика Intel\n• amf — видеокарты AMD\n• cpu — процессор (медленнее, но совместимо со всеми)",
        "codec": "Кодек сжатия видео:\n• H.264 — максимальная совместимость (телефоны, ТВ, веб)\n• H.265 (HEVC) — лучше сжатие, меньше размер (4K, современные устройства)",
        "cq": "Качество видео (1-51):\n• 18-22 — высокое качество (рекомендуется)\n• 23-28 — среднее качество\n• 29-51 — низкое качество, маленький размер\nМеньше = лучше качество, больше размер файла",
        "scale": "Изменить разрешение видео:\n• Нет — оставить как есть\n• 1920x (Full HD) — для ТВ и мониторов\n• 1280x (HD) — для веба и телефонов\n• 3840x (4K) — для 4K телевизоров",
        "audio": "Количество звуковых каналов:\n• 2 — стерео (наушники, телефоны, ТВ)\n• 6 — 5.1 surround (домашний кинотеатр)\n• 8 — 7.1 surround (профессиональное)",
        "container": "Формат файла:\n• MKV — универсальный, поддерживает всё\n• MP4 — максимальная совместимость с устройствами",
        "subs": "Если отмечено — субтитры будут удалены из видео",
    }
    
    def __init__(self, parent, preset_manager):
        super().__init__(parent)
        self.preset_manager = preset_manager
        self.current_preset = None
        self._init_ui()
        self._load_presets_list()
    
    def _init_ui(self):
        self.setWindowTitle("Конструктор пресетов")
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
        
        left_layout.addWidget(QLabel("<b>Сохранённые пресеты</b>"))
        
        self.presets_list = QListWidget()
        self.presets_list.setMinimumHeight(200)
        self.presets_list.itemSelectionChanged.connect(self._load_selected_preset)
        left_layout.addWidget(self.presets_list)
        
        # Кнопки управления
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.new_btn = QPushButton("➕ Новый")
        self.new_btn.clicked.connect(self._new_preset)
        btn_layout.addWidget(self.new_btn)
        
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.setStyleSheet("background-color: #15803d; color: white;")
        self.save_btn.clicked.connect(self._save_preset)
        btn_layout.addWidget(self.save_btn)
        
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setStyleSheet("background-color: #dc2626; color: white;")
        self.delete_btn.clicked.connect(self._delete_preset)
        btn_layout.addWidget(self.delete_btn)
        
        self.reset_btn = QPushButton("🔄 Сбросить")
        self.reset_btn.setStyleSheet("background-color: #0891b2; color: white;")
        self.reset_btn.clicked.connect(self._reset_presets)
        btn_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(btn_frame)
        left_layout.addStretch()
        
        # Информация
        info_box = QGroupBox("Справка")
        info_layout = QVBoxLayout(info_box)
        self.help_label = QLabel("Выберите пресет или создайте новый")
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
        self.name_input.setPlaceholderText("Введите название пресета")
        self.name_input.textChanged.connect(lambda: self._show_help("name"))
        self.form_layout.addRow("Название*", self.name_input)
        
        # Описание
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Краткое описание")
        self.desc_input.textChanged.connect(lambda: self._show_help("desc"))
        self.form_layout.addRow("Описание", self.desc_input)
        
        self.form_layout.addRow(QLabel("<hr/>"))
        
        # Ускорение
        self.hw_input = QComboBox()
        self.hw_input.addItems(["nvenc (NVIDIA)", "qsv (Intel)", "amf (AMD)", "cpu (Процессор)"])
        self.hw_input.currentTextChanged.connect(lambda: self._show_help("hw"))
        self.form_layout.addRow("Ускорение*", self.hw_input)
        
        # Кодек
        self.codec_input = QComboBox()
        self.codec_input.addItems(["H.264 (совместимость)", "H.265/HEVC (эффективность)"])
        self.codec_input.currentTextChanged.connect(lambda: self._show_help("codec"))
        self.form_layout.addRow("Кодек*", self.codec_input)
        
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
        self.form_layout.addRow("Качество (CQ)*", cq_frame)
        
        # Масштабирование
        self.scale_input = QComboBox()
        self.scale_input.addItems(["Нет (оригинал)", "1920x Full HD", "1280x HD", "3840x 4K"])
        self.scale_input.currentTextChanged.connect(lambda: self._show_help("scale"))
        self.form_layout.addRow("Масштаб", self.scale_input)
        
        self.form_layout.addRow(QLabel("<hr/>"))
        
        # Аудио каналы
        self.audio_input = QComboBox()
        self.audio_input.addItems(["2 (Стерео)", "6 (5.1 Surround)", "8 (7.1 Surround)"])
        self.audio_input.currentTextChanged.connect(lambda: self._show_help("audio"))
        self.form_layout.addRow("Аудио каналы*", self.audio_input)
        
        # Контейнер
        self.container_input = QComboBox()
        self.container_input.addItems(["MKV (универсальный)", "MP4 (совместимость)"])
        self.container_input.currentTextChanged.connect(lambda: self._show_help("container"))
        self.form_layout.addRow("Контейнер*", self.container_input)
        
        # Субтитры
        self.subs_input = QCheckBox("Удалить субтитры из видео")
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
        self.help_label.setText(self.HELP_TEXTS.get(key, ""))
    
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
            self.modified_label.setText("✏️ Изменено — сохраните пресет")
        else:
            self.modified_label.setText("✏️ Новый пресет — введите название и сохраните")
    
    def _load_presets_list(self):
        """Загрузить список пресетов"""
        self.presets_list.clear()
        
        for p in self.preset_manager.get_all_presets():
            icon = "📦 " if p.id.startswith("custom_") else "🔒 "
            item = QListWidgetItem(f"{icon}{p.name}")
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
            QMessageBox.warning(self, "Ошибка", "Введите название пресета")
            return
        
        # Проверка на встроенные пресеты
        if self.current_preset and not self.current_preset.id.startswith("custom_"):
            reply = QMessageBox.question(
                self, "Сохранение",
                "Это встроенный пресет. Сохранить как новый?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.preset_manager.add_preset(preset)
        self._load_presets_list()
        self.modified_label.setText("✓ Сохранено")
        
        # Обновить комбобокс в главном окне
        if self.parent() and hasattr(self.parent(), 'preset_combo'):
            self.parent().preset_combo.clear()
            self.parent().preset_combo.addItems([p.name for p in self.preset_manager.get_all_presets()])
    
    def _delete_preset(self):
        """Удалить выбранный пресет"""
        items = self.presets_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Удаление", "Сначала выберите пресет")
            return
        
        if not self.current_preset:
            QMessageBox.information(self, "Удаление", "Сначала выберите пресет")
            return
        
        if not self.current_preset.id.startswith("custom_"):
            QMessageBox.warning(
                self, "Нельзя удалить",
                "Встроенные пресеты удалять нельзя.\nСоздайте свой пресет с нужными параметрами."
            )
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить пресет '{self.current_preset.name}'?",
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
            "Восстановление пресетов",
            "⚠️  Все пользовательские пресеты будут удалены.\n"
            "Стандартные пресеты будут восстановлены.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Удаляем файл пользовательских пресетов
        import os
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
            self.parent().preset_combo.clear()
            self.parent().preset_combo.addItems([p.name for p in self.preset_manager.get_all_presets()])
        
        QMessageBox.information(
            self,
            "Готово",
            "✓ Стандартные пресеты восстановлены"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Converter")
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
        self.files_list = []  # Список кортежей (path, checkbox)
        self.selected_preset = None
        self.worker = None
        self.installer = None
        
        self._init_ui()
        self._check_ffmpeg()
    
    def _init_ui(self):
        # Центральное окно
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("FFmpeg Converter")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        self.status_label = QLabel("Проверка...")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # Баннер установки
        self.install_banner = QFrame()
        self.install_banner.setStyleSheet("background-color: #d97706; padding: 10px;")
        self.install_banner.hide()
        
        banner_layout = QHBoxLayout(self.install_banner)
        banner_layout.addWidget(QLabel("⚠️  FFmpeg не найден. Установите для работы."))
        
        install_btn = QPushButton("Установить")
        install_btn.setStyleSheet("QPushButton { background-color: #15803d; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #166534; }")
        install_btn.clicked.connect(self._install_ffmpeg)
        banner_layout.addWidget(install_btn)
        banner_layout.addStretch()
        
        layout.addWidget(self.install_banner)
        
        # Баннер обновления
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("background-color: #0284c7; padding: 10px;")
        self.update_banner.hide()
        
        update_layout = QHBoxLayout(self.update_banner)
        update_layout.addWidget(QLabel("🔄 Доступна новая версия FFmpeg"))
        
        update_btn = QPushButton("Обновить")
        update_btn.setStyleSheet("QPushButton { background-color: #15803d; color: white; padding: 8px 15px; border-radius: 4px; }")
        update_btn.clicked.connect(self._install_ffmpeg)
        update_layout.addWidget(update_btn)
        
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("QPushButton { background: transparent; border: 1px solid white; color: white; padding: 5px 10px; border-radius: 3px; } QPushButton:hover { background-color: #dc2626; }")
        dismiss_btn.clicked.connect(self.update_banner.hide)
        update_layout.addWidget(dismiss_btn)
        update_layout.addStretch()
        
        layout.addWidget(self.update_banner)
        
        # Выбор папки
        folder_frame = QGroupBox("Папка с файлами")
        folder_layout = QHBoxLayout(folder_frame)
        
        select_btn = QPushButton("📁 Выбрать папку")
        select_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(select_btn)
        
        self.folder_label = QLabel("Папка не выбрана")
        self.folder_label.setStyleSheet("color: #6b7280;")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch()
        
        layout.addWidget(folder_frame)
        
        # Пресеты
        preset_frame = QGroupBox("Настройки конвертации")
        preset_layout = QVBoxLayout(preset_frame)
        
        # Первая строка: комбобокс + кнопка
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Пресет:"), 0, Qt.AlignmentFlag.AlignRight)
        
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        self.preset_combo.setObjectName("preset_combo")
        presets = [p.name for p in self.preset_manager.get_all_presets()]
        self.preset_combo.addItems(presets)
        top_row.addWidget(self.preset_combo, 0, Qt.AlignmentFlag.AlignLeft)
        
        builder_btn = QPushButton("🛠 Конструктор")
        builder_btn.clicked.connect(self._open_preset_builder)
        top_row.addWidget(builder_btn)
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
        if presets:
            self.preset_combo.setCurrentIndex(0)
            self._preset_changed(presets[0])
        
        layout.addWidget(preset_frame)
        
        # Список файлов
        files_group = QGroupBox("Файлы")
        files_layout = QVBoxLayout(files_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setSpacing(2)
        self.files_layout.addStretch()
        
        scroll.setWidget(self.files_container)
        files_layout.addWidget(scroll)
        
        self.files_count = QLabel("Файлов: 0/0")
        self.files_count.setStyleSheet("color: #6b7280;")
        
        # Кнопки управления выделением
        select_btns = QHBoxLayout()
        select_btns.addWidget(self.files_count)
        select_btns.addStretch()
        
        select_all_btn = QPushButton("✓ Все")
        select_all_btn.setMaximumWidth(80)
        select_all_btn.clicked.connect(self._select_all_files)
        select_btns.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("✗ Все")
        deselect_all_btn.setMaximumWidth(80)
        deselect_all_btn.clicked.connect(self._deselect_all_files)
        select_btns.addWidget(deselect_all_btn)
        
        files_layout.addLayout(select_btns)
        
        layout.addWidget(files_group, 1)
        
        # Прогресс
        progress_group = QGroupBox("Конвертация")
        progress_layout = QHBoxLayout(progress_group)
        
        self.convert_btn = QPushButton("▶ Конвертировать")
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet("QPushButton { background-color: #2563eb; color: white; font-size: 13px; font-weight: bold; border-radius: 4px; padding: 10px; } QPushButton:hover { background-color: #1d4ed8; } QPushButton:disabled { background-color: #4b5563; }")
        self.convert_btn.clicked.connect(self._convert)
        progress_layout.addWidget(self.convert_btn)
        
        self.cancel_btn = QPushButton("⏹ Стоп")
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
        
        layout.addWidget(progress_group)
        
        # Лог
        log_group = QGroupBox("Лог операций")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.convert_status = QLabel("")
        self.status_bar.addWidget(self.convert_status)
    
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
            self.status_label.setText(f"✓ FFmpeg {self.ffmpeg_version}")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            self.status_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.install_banner.hide()
            QTimer.singleShot(8000, self._check_updates)
        else:
            self.status_label.setText("✗ FFmpeg не найден")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            self.install_banner.show()
    
    def _check_updates(self):
        try:
            if FFmpegUpdater.should_notify():
                self.update_banner.show()
        except:
            pass
    
    def _open_preset_builder(self):
        """Открыть конструктор пресетов"""
        dlg = PresetBuilderDialog(self, self.preset_manager)
        dlg.show()
    
    def _ffmpeg_menu(self, event):
        if not self.ffmpeg_available:
            return
        
        platform = PlatformManager.get_platform()
        install_dir = platform.get_ffmpeg_install_path()
        
        menu = QMenu(self)
        menu.addAction(f"✓ FFmpeg {self.ffmpeg_version}")
        menu.addSeparator()
        menu.addAction("📁 Открыть папку", lambda: platform.open_file_explorer(install_dir))
        menu.addAction("🗑️ Удалить", self._uninstall_ffmpeg)
        
        menu.exec(self.status_label.mapToGlobal(event.pos()))
    
    def _uninstall_ffmpeg(self):
        if FFmpegInstaller.uninstall():
            self._log("✓ FFmpeg удалён")
            self._check_ffmpeg()
        else:
            self.status_bar.showMessage("✗ Ошибка удаления", 3000)
    
    def _install_ffmpeg(self):
        if self.installer and self.installer.isRunning():
            return
        
        self.update_banner.hide()
        self.installer = InstallerThread()
        self.installer.progress.connect(lambda p: self.status_bar.showMessage(f"Установка... {p}%", 2000))
        self.installer.finished.connect(self._install_done)
        self.installer.start()
    
    def _install_done(self, ok):
        self._check_ffmpeg()
        if ok:
            self._log(f"✓ FFmpeg установлен: {FFmpegInstaller.get_ffmpeg_version()}")
    
    def _select_folder(self):
        # По умолчанию открываем папку пользователя
        default_dir = str(Path.home())
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Папка с файлами",
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
            
            for f in Path(folder).iterdir():
                if f.is_file() and f.suffix.lower() in exts:
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
                    
                    label = QLabel(f"{f.name}  —  {f.stat().st_size // 1024} KB")
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
        self.files_count.setText(f"Файлов: {selected}/{total}")
    
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
        p = self.preset_manager.get_preset_by_name(name)
        if p:
            self.selected_preset = p
            self.preset_info.setText(p.description)
    
    def _convert(self):
        if not self.ffmpeg_available:
            self.convert_status.setText("✗ FFmpeg не найден")
            self.convert_status.setStyleSheet("color: #ef4444;")
            return
        
        # Получаем выбранные файлы
        selected_files = self._get_selected_files()
        
        if not selected_files:
            self.convert_status.setText("⚠️ Выберите файлы")
            self.convert_status.setStyleSheet("color: #f59e0b;")
            return
        
        if not self.selected_preset:
            self.convert_status.setText("⚠️ Нет пресета")
            self.convert_status.setStyleSheet("color: #f59e0b;")
            return
        
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected_files))
        self.convert_status.setText("Конвертация...")
        self.convert_status.setStyleSheet("color: #f59e0b;")
        
        out = Path(self.selected_folder) / "output"
        out.mkdir(exist_ok=True)
        
        self.worker = WorkerThread(selected_files, out, self.selected_preset, self.ffmpeg)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_done)
        self.worker.log.connect(self._log)
        self.worker.start()
    
    def _cancel_conversion(self):
        """Отмена конвертации"""
        if self.worker and self.worker.isRunning():
            self.worker.kill()  # Мгновенное завершение ffmpeg.exe
            self.convert_status.setText("⚠️ Отмена...")
            self.convert_status.setStyleSheet("color: #f59e0b;")
    
    def _on_progress(self, current, name):
        """Обновление прогресса"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(name)
    
    def _on_done(self, ok, err):
        """Завершение конвертации"""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        total = ok + err
        if err == 0:
            self.convert_status.setText(f"✓ Готово: {ok}/{total}")
            self.convert_status.setStyleSheet("color: #22c55e;")
        else:
            self.convert_status.setText(f"⚠️ {ok} успешно, {err} ошибок")
            self.convert_status.setStyleSheet("color: #f59e0b;")
        self._log(f"=== {ok} успешно, {err} ошибок ===")
    
    def _log(self, msg):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {msg}")


def main():
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
