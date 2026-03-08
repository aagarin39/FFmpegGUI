import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
import shutil

# Импорт для работы в скомпилированном приложении
if getattr(sys, 'frozen', False):
    import src.core.ffmpeg
    import src.core.presets
    import src.core.ffmpeg_installer
    import src.core.ffmpeg_updater
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
    PresetManager = src.core.presets.PresetManager
    Preset = src.core.presets.Preset
    FFmpegInstaller = src.core.ffmpeg_installer.FFmpegInstaller
    FFmpegUpdater = src.core.ffmpeg_updater.FFmpegUpdater
else:
    try:
        from .core.ffmpeg import FFmpegWrapper
        from .core.presets import PresetManager, Preset
        from .core.ffmpeg_installer import FFmpegInstaller
        from .core.ffmpeg_updater import FFmpegUpdater
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.presets import PresetManager, Preset
        from core.ffmpeg_installer import FFmpegInstaller
        from core.ffmpeg_updater import FFmpegUpdater


class ConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FFmpeg Converter")
        self.geometry("1000x700")
        self.minsize(800, 600)  # Минимальный размер

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Состояние приложения
        self.ffmpeg_available = False
        self.ffmpeg_version = ""
        self.is_installing = False
        self.install_progress = 0
        self.has_update = False
        
        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()

        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None
        self.is_converting = False

        self.create_widgets()
        
        # Проверка состояния после создания виджетов
        self.after(100, self._initialize_ffmpeg_status)

    def _initialize_ffmpeg_status(self):
        """Инициализация статуса FFmpeg"""
        self._check_ffmpeg_and_update()

    def _check_ffmpeg(self) -> bool:
        """Проверка наличия FFmpeg в системе."""
        # Проверяем папку установки
        install_dir = Path.home() / "FFmpegGUI" / "ffmpeg"
        
        if (install_dir / "ffmpeg.exe").exists():
            return True
        
        # Проверяем в PATH
        if shutil.which("ffmpeg"):
            return True
        
        return False

    def _check_ffmpeg_and_update(self):
        """Проверить FFmpeg и обновить интерфейс"""
        self.ffmpeg_available = self._check_ffmpeg()
        
        if self.ffmpeg_available:
            self.ffmpeg_version = FFmpegInstaller.get_ffmpeg_version()
            self._show_ffmpeg_installed()
        else:
            self._show_ffmpeg_not_installed()

    def _show_ffmpeg_installed(self):
        """Показать что FFmpeg установлен"""
        self.ffmpeg_status_label.configure(
            text=f"✓ FFmpeg {self.ffmpeg_version}",
            text_color="green"
        )
        self.ffmpeg_status_label.bind("<Button-1>", lambda e: self._create_ffmpeg_context_menu())
        self.ffmpeg_status_label.configure(cursor="hand2")
        
        # Скрываем баннер установки
        if hasattr(self, 'install_banner_frame'):
            self.install_banner_frame.grid_remove()
        
        # Проверяем обновления (фоново, раз в 7 дней)
        self._check_for_updates()

    def _show_ffmpeg_not_installed(self):
        """Показать что FFmpeg не установлен"""
        self.ffmpeg_status_label.configure(
            text="✗ FFmpeg не найден",
            text_color="red"
        )
        self.ffmpeg_status_label.unbind("<Button-1>")
        self.ffmpeg_status_label.configure(cursor="")
        
        # Показываем баннер установки
        if hasattr(self, 'install_banner_frame'):
            self.install_banner_frame.grid()
        
        # Скрываем баннер обновления если был показан
        if hasattr(self, 'update_banner_frame'):
            self.update_banner_frame.grid_remove()

    def _check_update_banner(self):
        """Проверить и показать баннер обновления"""
        self.has_update = FFmpegUpdater.should_notify()
        
        if hasattr(self, 'update_banner_frame'):
            if self.has_update:
                self.update_banner_frame.grid()
            else:
                self.update_banner_frame.grid_forget()

    # ========== Создание виджетов ==========
    
    def create_widgets(self):
        # Настройка масштабирования
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Banner
        self.grid_rowconfigure(2, weight=0)  # Folder
        self.grid_rowconfigure(3, weight=0)  # Preset
        self.grid_rowconfigure(4, weight=1)  # Files (растягивается)
        self.grid_rowconfigure(5, weight=0)  # Progress
        self.grid_rowconfigure(6, weight=0)  # Log

        # ===== Заголовок =====
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, pady=10, padx=20, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        
        ctk.CTkLabel(
            header_frame,
            text="FFmpeg Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Индикатор статуса FFmpeg
        self.ffmpeg_status_label = ctk.CTkLabel(
            header_frame,
            text="Проверка...",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.ffmpeg_status_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # ===== Баннер установки FFmpeg =====
        self.install_banner_frame = ctk.CTkFrame(self, fg_color="#d97706")
        self.install_banner_frame.grid(row=1, column=0, pady=5, padx=20, sticky="ew")
        self.install_banner_frame.grid_columnconfigure(0, weight=1)
        
        install_label = ctk.CTkLabel(
            self.install_banner_frame,
            text="⚠️  Для работы приложения необходим FFmpeg. Установите его для продолжения.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        )
        install_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        self.btn_install_banner = ctk.CTkButton(
            self.install_banner_frame,
            text="Установить FFmpeg",
            command=self._start_installation,
            width=160,
            height=36,
            fg_color="#15803d",
            hover_color="#166534",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_install_banner.grid(row=0, column=1, padx=20, pady=15)

        # ===== Баннер обновления FFmpeg =====
        self.update_banner_frame = ctk.CTkFrame(self, fg_color="#0284c7")
        self.update_banner_frame.grid(row=1, column=0, pady=5, padx=20, sticky="ew")
        self.update_banner_frame.grid_columnconfigure(0, weight=1)
        
        update_label = ctk.CTkLabel(
            self.update_banner_frame,
            text="🔄 Доступна новая версия FFmpeg",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        )
        update_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        update_btn_frame = ctk.CTkFrame(self.update_banner_frame, fg_color="transparent")
        update_btn_frame.grid(row=0, column=1, padx=20, pady=15)
        
        ctk.CTkButton(
            update_btn_frame,
            text="Обновить",
            command=self._start_installation,
            width=100,
            height=32,
            fg_color="#15803d",
            hover_color="#166534",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            update_btn_frame,
            text="✕",
            command=self._dismiss_update,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#dc2626",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"),
            border_width=1,
            border_color="white"
        ).pack(side="left", padx=5)

        # ===== Выбор папки =====
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=2, column=0, pady=10, padx=20, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        self.btn_select_folder = ctk.CTkButton(
            folder_frame,
            text="📁 Выбрать папку",
            command=self.select_folder,
            width=150
        )
        self.btn_select_folder.grid(row=0, column=0, padx=10, pady=10)

        self.lbl_folder = ctk.CTkLabel(
            folder_frame,
            text="Папка не выбрана",
            text_color="gray"
        )
        self.lbl_folder.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # ===== Выбор пресета =====
        preset_frame = ctk.CTkFrame(self)
        preset_frame.grid(row=3, column=0, pady=10, padx=20, sticky="ew")

        self.preset_var = ctk.StringVar(value="")
        preset_names = [p.name for p in self.preset_manager.get_all_presets()]
        
        self.cmb_preset = ctk.CTkComboBox(
            preset_frame,
            values=preset_names,
            variable=self.preset_var,
            command=self._on_preset_change,
            width=300
        )
        self.cmb_preset.grid(row=0, column=0, padx=10, pady=10)
        
        ctk.CTkButton(
            preset_frame,
            text="🛠 Конструктор",
            command=self.open_preset_builder,
            width=150
        ).grid(row=0, column=1, padx=10, pady=10)

        self.lbl_preset_info = ctk.CTkLabel(
            preset_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_preset_info.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # ===== Список файлов =====
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=4, column=0, pady=10, padx=20, sticky="nsew")
        self.grid_rowconfigure(4, weight=1)

        self.files_listbox = ctk.CTkScrollableFrame(files_frame)
        self.files_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.lbl_file_count = ctk.CTkLabel(
            files_frame,
            text="Файлов: 0",
            text_color="gray"
        )
        self.lbl_file_count.pack(padx=10, pady=5, anchor="w")

        # ===== Прогресс и конвертация =====
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=5, column=0, pady=10, padx=20, sticky="ew")

        self.btn_convert = ctk.CTkButton(
            progress_frame,
            text="▶ Конвертировать",
            command=self.start_conversion,
            width=200,
            height=40
        )
        self.btn_convert.grid(row=0, column=0, padx=10, pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)
        progress_frame.grid_columnconfigure(1, weight=1)

        self.lbl_progress = ctk.CTkLabel(progress_frame, text="")
        self.lbl_progress.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.lbl_status = ctk.CTkLabel(progress_frame, text="", text_color="green")
        self.lbl_status.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # ===== Лог =====
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=6, column=0, pady=10, padx=20, sticky="ew")

        ctk.CTkLabel(
            log_frame,
            text="Лог операций:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.log_text = ctk.CTkTextbox(log_frame, height=100, state="disabled")
        self.log_text.pack(fill="x", padx=10, pady=10)
        
        # Скрываем баннер установки изначально (покажется если FFmpeg не найден)
        if hasattr(self, 'install_banner_frame'):
            self.install_banner_frame.grid_remove()
        
        # Скрываем баннер обновления изначально
        if hasattr(self, 'update_banner_frame'):
            self.update_banner_frame.grid_remove()

    # ========== Установка FFmpeg ==========
    
    def _start_installation(self):
        """Начать установку FFmpeg"""
        if self.is_installing:
            return
        
        self.is_installing = True
        self.install_progress = 0
        
        # Обновляем кнопку с прогрессом
        self._update_install_button()
        
        # Скрываем баннер обновления если есть
        if hasattr(self, 'update_banner_frame'):
            self.update_banner_frame.grid_remove()
        
        # Запускаем установку в потоке
        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()
    
    def _update_install_button(self):
        """Обновить кнопку установки с прогрессом"""
        if self.is_installing:
            percent = int(self.install_progress * 100)
            self.btn_install_banner.configure(
                text=f"⏳ Установка... {percent}%",
                fg_color="#059669",  # Зелёный с прогрессом
                state="disabled"
            )
        else:
            self.btn_install_banner.configure(
                text="Установить FFmpeg",
                fg_color="#15803d",
                state="normal"
            )

    def _run_installation(self):
        """Установка FFmpeg в фоне"""
        def progress_callback(status: str, percent: float):
            self.install_progress = percent
            self.after(0, self._update_install_button)
        
        def on_complete(success: bool):
            self.is_installing = False
            
            if success:
                self.after(0, lambda: self.btn_install_banner.configure(
                    text="✓ Установлено",
                    fg_color="green",
                    state="disabled"
                ))
                # Обновляем статус через 2 секунды
                self.after(2000, self._after_install_success)
            else:
                self.after(0, lambda: self.btn_install_banner.configure(
                    text="Установить снова",
                    fg_color="#dc2626",  # Красный
                    state="normal"
                ))
        
        success = FFmpegInstaller.install(progress_callback)
        self.after(0, lambda: on_complete(success))

    def _after_install_success(self):
        """После успешной установки"""
        self._check_ffmpeg_and_update()
        self.btn_install_banner.configure(state="normal")
        
        messagebox.showinfo(
            "Готово",
            "FFmpeg успешно установлен!\n\n"
            f"Версия: {FFmpegInstaller.get_ffmpeg_version()}\n"
            f"Теперь можно конвертировать файлы."
        )

    def _dismiss_update(self):
        """Скрыть баннер обновления"""
        if hasattr(self, 'update_banner_frame'):
            self.update_banner_frame.grid_remove()

    def _check_for_updates(self):
        """Фоновая проверка обновлений"""
        if FFmpegUpdater.should_notify():
            self.has_update = True
            if hasattr(self, 'update_banner_frame'):
                self.update_banner_frame.grid()

    # ========== Контекстное меню FFmpeg ==========
    
    def _create_ffmpeg_context_menu(self):
        """Контекстное меню для управления FFmpeg"""
        if not self.ffmpeg_available:
            return
        
        # Создаём окно с фиксированным размером
        dialog = ctk.CTkToplevel(self)
        dialog.title("Управление FFmpeg")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Главный контейнер
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        ctk.CTkLabel(
            main_frame,
            text=f"✓ FFmpeg {self.ffmpeg_version}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="green"
        ).pack(pady=(0, 20))
        
        # Информация
        info_frame = ctk.CTkFrame(main_frame, fg_color="#1f2937")
        info_frame.pack(fill="x", pady=10)
        
        install_date = FFmpegInstaller.get_install_date()
        install_dir = str(FFmpegInstaller.INSTALL_DIR)
        
        ctk.CTkLabel(
            info_frame,
            text=f"📅 Установлен: {install_date}",
            justify="left",
            text_color="#9ca3af"
        ).pack(anchor="w", padx=20, pady=15)
        
        ctk.CTkLabel(
            info_frame,
            text=f"📁 Путь: {install_dir}",
            justify="left",
            wraplength=440,
            text_color="#9ca3af"
        ).pack(anchor="w", padx=20, pady=(0,15))
        
        # Статус обновлений
        self.update_status_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=12), wraplength=440)
        self.update_status_label.pack(pady=10)
        
        # Кнопки
        ctk.CTkButton(
            main_frame,
            text="📁 Открыть папку",
            command=lambda: subprocess.run(["explorer", install_dir]),
            height=44,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="white",
            font=ctk.CTkFont(size=14)
        ).pack(fill="x", pady=8)
        
        self.btn_check_update = ctk.CTkButton(main_frame, text="🔄 Проверить обновления", command=lambda: self._manual_check_update(dialog), height=44, fg_color="#d97706", hover_color="#b45309", text_color="white", font=ctk.CTkFont(size=14))
        self.btn_check_update.pack(fill="x", pady=8)
        
        ctk.CTkButton(
            main_frame,
            text="🗑️ Удалить FFmpeg",
            command=lambda: self._uninstall_ffmpeg(dialog),
            height=44,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="white",
            font=ctk.CTkFont(size=14)
        ).pack(fill="x", pady=8)
        
        # Разделитель
        ctk.CTkFrame(main_frame, height=2, fg_color="#374151").pack(fill="x", pady=15)
        
        ctk.CTkButton(
            main_frame,
            text="Закрыть",
            command=dialog.destroy,
            height=40,
            fg_color="transparent",
            border_width=2,
            border_color="#4b5563",
            text_color="white",
            hover_color="#374151",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 Проверить обновления",
            command=on_check_update,
            width=180,
            fg_color="#d97706",
            hover_color="#b45309",
            text_color="white"
        ).pack(pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ Удалить FFmpeg",
            command=on_uninstall,
            width=180,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="white"
        ).pack(pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Закрыть",
            command=self.context_menu.destroy,
            width=180,
            fg_color="transparent",
            border_width=1,
            border_color="#4b5563",
            text_color="white",
            hover_color="#374151"
        ).pack(pady=5)

    def _manual_check_update(self, dialog):
        """Ручная проверка обновлений"""
        # Блокируем кнопку
        self.btn_check_update.configure(state="disabled", text="⏳ Проверка...")
        
        # Показываем статус
        self.update_status_label.configure(
            text="🔄 Проверка обновлений...",
            text_color="#fcd34d"
        )
        
        def check_thread():
            try:
                update_info = FFmpegUpdater.check_for_update()
                dialog.after(0, lambda: self._show_update_result(dialog, update_info))
            except Exception as e:
                dialog.after(0, lambda: self._show_update_error(dialog, str(e)))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _show_update_result(self, dialog, update_info):
        """Показать результат проверки"""
        self.btn_check_update.configure(state="normal", text="🔄 Проверить обновления")
        
        if update_info:
            # Найдено обновление
            self.update_status_label.configure(
                text=f"🔄 Доступна версия {update_info['version']} от {update_info['date']}",
                text_color="#fcd34d"
            )
            
            # Добавляем кнопку установки
            install_btn = ctk.CTkButton(
                dialog,
                text="⬇️ Установить обновление",
                command=lambda: [dialog.destroy(), self._start_installation()],
                height=44,
                fg_color="#15803d",
                hover_color="#166534",
                text_color="white",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            install_btn.pack(pady=10)
        else:
            # Обновлений нет
            self.update_status_label.configure(
                text="✓ Установлена последняя версия",
                text_color="#86efac"
            )
    
    def _show_update_error(self, dialog, error_msg):
        """Показать ошибку проверки"""
        self.btn_check_update.configure(state="normal", text="🔄 Проверить обновления")
        
        self.update_status_label.configure(
            text=f"⚠️ Ошибка: {error_msg}",
            text_color="#fca5a5"
        )
    
    def _uninstall_ffmpeg(self, dialog):
        """Удалить FFmpeg"""
        result = messagebox.askyesno(
            "Удаление FFmpeg",
            "⚠️ FFmpeg будет удалён.\nПриложение не сможет работать без FFmpeg.\n\nПродолжить?",
            icon=messagebox.WARNING
        )
        if result:
            success = FFmpegInstaller.uninstall()
            if success:
                messagebox.showinfo("Удалено", "FFmpeg успешно удалён")
                dialog.destroy()
                self._check_ffmpeg_and_update()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить FFmpeg")
        check_label.pack(pady=5)
        
        def check_thread():
            try:
                update_info = FFmpegUpdater.check_for_update()
                
                # Удаляем индикатор и показываем результат
                self.after(0, lambda: [
                    check_frame.destroy(),
                    self._show_update_result(update_info, btn_frame)
                ])
            except Exception as e:
                self.after(0, lambda: [
                    check_frame.destroy(),
                    self._show_update_error(str(e), btn_frame)
                ])
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def _on_preset_change(self, value):
        if not value:
            return
        preset = self.preset_manager.get_preset_by_name(value)
        if preset:
            self.selected_preset = preset
            self.lbl_preset_info.configure(text=preset.description)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с файлами")
        if folder:
            self.selected_folder = folder
            self.lbl_folder.configure(text=folder)
            self.files_list = []

            for widget in self.files_listbox.winfo_children():
                widget.destroy()

            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}

            for file in Path(folder).iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions | image_extensions:
                    self.files_list.append(str(file))
                    file_frame = ctk.CTkFrame(self.files_listbox)
                    file_frame.pack(fill="x", pady=2)
                    
                    ctk.CTkLabel(
                        file_frame,
                        text=file.name,
                        width=600,
                        anchor="w"
                    ).pack(side="left", padx=10, pady=5)
                    
                    ctk.CTkLabel(
                        file_frame,
                        text=f"{file.stat().st_size // 1024} KB",
                        text_color="gray",
                        width=100
                    ).pack(side="right", padx=10, pady=5)

            self.lbl_file_count.configure(text=f"Файлов: {len(self.files_list)}")

    def log_message(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_conversion(self):
        if not self.ffmpeg_available:
            messagebox.showerror(
                "Ошибка",
                "FFmpeg не найден!\n\n"
                "Установите FFmpeg для продолжения."
            )
            return
            
        if not self.selected_folder or not self.files_list:
            messagebox.showwarning("Внимание", "Выберите папку с файлами!")
            return
            
        if not self.selected_preset:
            messagebox.showwarning("Внимание", "Выберите пресет конвертации!")
            return

        self.is_converting = True
        self.btn_convert.configure(state="disabled")
        self.btn_select_folder.configure(state="disabled")
        self.cmb_preset.configure(state="disabled")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Конвертация...", text_color="orange")

        thread = threading.Thread(target=self._run_conversion, daemon=True)
        thread.start()

    def _run_conversion(self):
        # Логика конвертации
        pass

    def open_preset_builder(self):
        # Конструктор пресетов
        pass


if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()
