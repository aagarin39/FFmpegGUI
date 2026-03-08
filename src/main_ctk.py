import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import asyncio
import sys
import shutil
import ctypes

# Импорт для работы в скомпилированном приложении
if getattr(sys, 'frozen', False):
    # Запуск из exe - используем абсолютные импорты
    import src.core.ffmpeg
    import src.core.presets
    import src.core.ffmpeg_installer
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
    PresetManager = src.core.presets.PresetManager
    Preset = src.core.presets.Preset
    FFmpegInstaller = src.core.ffmpeg_installer.FFmpegInstaller
else:
    # Запуск из исходников
    try:
        from .core.ffmpeg import FFmpegWrapper
        from .core.presets import PresetManager, Preset
        from .core.ffmpeg_installer import FFmpegInstaller
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.presets import PresetManager, Preset
        from core.ffmpeg_installer import FFmpegInstaller


class ConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FFmpeg Converter")
        self.geometry("1000x700")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Проверка наличия FFmpeg
        self.ffmpeg_available = self._check_ffmpeg()
        
        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()

        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None
        self.is_converting = False

        self.create_widgets()
        
        # Показать предупреждение если FFmpeg не найден
        if not self.ffmpeg_available:
            self._show_ffmpeg_warning()

    def _check_ffmpeg(self) -> bool:
        """Проверка наличия FFmpeg в системе."""
        # Проверяем в PATH
        if shutil.which("ffmpeg"):
            return True
        
        # Проверяем папку установки
        install_dir = Path.home() / "FFmpegGUI" / "ffmpeg"
        if (install_dir / "ffmpeg.exe").exists():
            return True
        
        # Проверяем локальную папку ffmpeg
        local_ffmpeg = Path(__file__).parent.parent / "ffmpeg"
        if local_ffmpeg.exists():
            if sys.platform == "win32":
                return (local_ffmpeg / "ffmpeg.exe").exists()
            else:
                return (local_ffmpeg / "ffmpeg").exists()
        
        return False

    def _show_ffmpeg_warning(self):
        """Показать предупреждение об отсутствии FFmpeg с предложением установки."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("FFmpeg не найден")
        dialog.geometry("600x450")
        dialog.transient(self)
        dialog.grab_set()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        ctk.CTkLabel(
            main_frame,
            text="FFmpeg не найден в системе",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="red"
        ).pack(pady=10)
        
        # Описание
        description = """Для работы приложения необходим FFmpeg.

Вы можете установить его автоматически:
• FFmpeg будет загружен с официального GitHub-репозитория
• Установлен в папку пользователя: %USERPROFILE%\\FFmpegGUI\\ffmpeg
• Добавлен в PATH пользователя

Не требуются права администратора."""
        
        ctk.CTkLabel(
            main_frame,
            text=description,
            justify="left",
            font=ctk.CTkFont(size=12)
        ).pack(pady=10, padx=20)
        
        # Прогресс бар
        self.install_progress = ctk.CTkProgressBar(main_frame)
        self.install_progress.pack(pady=10, padx=20, fill="x")
        self.install_progress.set(0)
        
        self.install_status = ctk.CTkLabel(main_frame, text="", text_color="gray")
        self.install_status.pack(pady=5)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(pady=20)
        
        def on_install():
            self.btn_install.configure(state="disabled")
            self.btn_cancel.configure(state="disabled")
            self._run_installation()
        
        self.btn_install = ctk.CTkButton(
            btn_frame,
            text="Установить FFmpeg",
            command=on_install,
            width=200,
            height=35
        )
        self.btn_install.pack(side="left", padx=10)
        
        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Отмена",
            command=lambda: dialog.destroy(),
            width=150,
            height=35
        )
        self.btn_cancel.pack(side="left", padx=10)
        
        # Ссылка на ручной вариант
        manual_text = """Или установите вручную:
1. Скачайте с https://github.com/BtbN/FFmpeg-Builds/releases
2. Распакуйте в удобное место
3. Добавьте папку bin в системный PATH"""
        
        ctk.CTkLabel(
            main_frame,
            text=manual_text,
            justify="left",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(pady=10)
    
    def _run_installation(self):
        """Запуск установки FFmpeg."""
        def progress_callback(status: str, percent: float):
            self.install_status.configure(text=status)
            self.install_progress.set(percent / 100)
            self.update()
        
        def install_thread():
            success = FFmpegInstaller.install(progress_callback)
            
            if success:
                self.after(0, lambda: messagebox.showinfo(
                    "Успех",
                    "FFmpeg успешно установлен!\n\nПерезапустите приложение для применения изменений."
                ))
                self.after(0, lambda: self.quit())
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Ошибка",
                    "Не удалось установить FFmpeg.\nПопробуйте установить вручную."
                ))
                self.after(0, lambda: self.btn_install.configure(state="normal"))
                self.after(0, lambda: self.btn_cancel.configure(state="normal"))
        
        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(
            self,
            text="FFmpeg Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=10, padx=20)
        
        # Индикатор статуса FFmpeg
        ffmpeg_status_frame = ctk.CTkFrame(self)
        ffmpeg_status_frame.grid(row=0, column=0, sticky="ne", padx=20, pady=10)
        
        self.ffmpeg_status_label = ctk.CTkLabel(
            ffmpeg_status_frame,
            text="✓ FFmpeg найден" if self.ffmpeg_available else "✗ FFmpeg не найден",
            text_color="green" if self.ffmpeg_available else "red",
            font=ctk.CTkFont(size=11)
        )
        self.ffmpeg_status_label.pack(padx=10, pady=5)
        
        # Кнопка установки FFmpeg (если не найден)
        if not self.ffmpeg_available:
            self.btn_install_ffmpeg = ctk.CTkButton(
                ffmpeg_status_frame,
                text="Установить FFmpeg",
                command=self._show_ffmpeg_warning,
                width=150,
                height=25,
                fg_color="orange"
            )
            self.btn_install_ffmpeg.pack(padx=10, pady=5)

        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        self.btn_select_folder = ctk.CTkButton(
            folder_frame,
            text="Выбрать папку",
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

        preset_frame = ctk.CTkFrame(self)
        preset_frame.grid(row=2, column=0, pady=10, padx=20, sticky="ew")

        self.preset_var = ctk.StringVar(value="")
        preset_names = [p.name for p in self.preset_manager.get_all_presets()]
        
        self.cmb_preset = ctk.CTkComboBox(
            preset_frame,
            values=preset_names,
            variable=self.preset_var,
            command=self.on_preset_change,
            width=300
        )
        self.cmb_preset.grid(row=0, column=0, padx=10, pady=10)

        self.btn_preset_builder = ctk.CTkButton(
            preset_frame,
            text="Конструктор",
            command=self.open_preset_builder,
            width=150
        )
        self.btn_preset_builder.grid(row=0, column=1, padx=10, pady=10)

        self.lbl_preset_info = ctk.CTkLabel(
            preset_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_preset_info.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=3, column=0, pady=10, padx=20, sticky="nsew")

        self.files_listbox = ctk.CTkScrollableFrame(files_frame)
        self.files_listbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_file_count = ctk.CTkLabel(
            files_frame,
            text="Файлов: 0",
            text_color="gray"
        )
        self.lbl_file_count.pack(padx=10, pady=5, anchor="w")

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=4, column=0, pady=10, padx=20, sticky="ew")

        self.btn_convert = ctk.CTkButton(
            progress_frame,
            text="Конвертировать",
            command=self.start_conversion,
            width=200,
            height=40
        )
        self.btn_convert.grid(row=0, column=0, padx=10, pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)  # Сброс в 0
        progress_frame.grid_columnconfigure(1, weight=1)

        self.lbl_progress = ctk.CTkLabel(progress_frame, text="")
        self.lbl_progress.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.lbl_status = ctk.CTkLabel(progress_frame, text="", text_color="green")
        self.lbl_status.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=5, column=0, pady=10, padx=20, sticky="ew")

        ctk.CTkLabel(
            log_frame,
            text="Лог:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.log_text = ctk.CTkTextbox(log_frame, height=100, state="disabled")
        self.log_text.pack(fill="x", padx=10, pady=10)

    def log_message(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

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

    def on_preset_change(self, value):
        if not value:
            return
        preset = self.preset_manager.get_preset_by_name(value)
        if preset:
            self.selected_preset = preset
            self.lbl_preset_info.configure(text=preset.description)

    def open_preset_builder(self):
        """Открыть конструктор пресетов."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Конструктор пресетов")
        dialog.geometry("550x680")
        dialog.transient(self)
        dialog.grab_set()
        
        # Устанавливаем тёмную тему для диалога
        dialog._set_appearance_mode("dark")
        
        # Прокручиваемый контент с темным фоном
        scroll_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        row = 0
        
        # Заголовок с описанием
        ctk.CTkLabel(
            scroll_frame,
            text="Создание пользовательского пресета",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, pady=(0, 15), sticky="w")
        row += 1
        
        ctk.CTkLabel(
            scroll_frame,
            text="Настройте параметры конвертации и сохраните как новый пресет",
            text_color="gray",
            font=ctk.CTkFont(size=11),
            justify="left"
        ).grid(row=row, column=0, pady=(0, 20), sticky="w")
        row += 1
        
        # Название пресета
        ctk.CTkLabel(
            scroll_frame,
            text="Название пресета *",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        name_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Например: Мой пресет")
        name_entry.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        row += 1
        
        # Описание
        ctk.CTkLabel(
            scroll_frame,
            text="Описание",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        desc_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Краткое описание пресета")
        desc_entry.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        row += 1
        
        # Видео кодек
        ctk.CTkLabel(
            scroll_frame,
            text="Видео кодек",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        codec_var = ctk.StringVar(value="h264_nvenc")
        codec_combo = ctk.CTkComboBox(
            scroll_frame,
            values=["h264_nvenc", "hevc_nvenc"],
            variable=codec_var,
            command=lambda x: None
        )
        codec_combo.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        ctk.CTkLabel(
            scroll_frame,
            text="h264_nvenc - быстрее, hevc_nvenc - лучше сжатие",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).grid(row=row+1, column=0, sticky="w", pady=(0, 10))
        row += 2
        
        # CQ качество
        ctk.CTkLabel(
            scroll_frame,
            text="CQ (качество 1-51)",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        cq_entry = ctk.CTkEntry(scroll_frame)
        cq_entry.insert(0, "20")
        cq_entry.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        ctk.CTkLabel(
            scroll_frame,
            text="Меньше = лучше качество, больше = меньше размер (18-28 оптимально)",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).grid(row=row+1, column=0, sticky="w", pady=(0, 10))
        row += 2
        
        # Масштабирование
        ctk.CTkLabel(
            scroll_frame,
            text="Масштабирование",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        scale_var = ctk.StringVar(value="")
        scale_combo = ctk.CTkComboBox(
            scroll_frame,
            values=["", "1920:-2", "1280:-2", "3840:-2"],
            variable=scale_var,
            command=lambda x: None
        )
        scale_combo.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        ctk.CTkLabel(
            scroll_frame,
            text="1920:-2 - Full HD, 1280:-2 - HD, 3840:-2 - 4K, пусто - без изменений",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).grid(row=row+1, column=0, sticky="w", pady=(0, 10))
        row += 2
        
        # Чекбоксы
        remove_subs_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll_frame,
            text="Удалить субтитры",
            variable=remove_subs_var
        ).grid(row=row, column=0, padx=0, pady=10, sticky="w")
        row += 1
        
        stabilize_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll_frame,
            text="Стабилизация видео (медленнее, но убирает дрожание)",
            variable=stabilize_var
        ).grid(row=row, column=0, padx=0, pady=10, sticky="w")
        row += 1
        
        # Контейнер
        ctk.CTkLabel(
            scroll_frame,
            text="Контейнер",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        container_var = ctk.StringVar(value="mkv")
        container_combo = ctk.CTkComboBox(
            scroll_frame,
            values=["mkv", "mp4"],
            variable=container_var,
            command=lambda x: None
        )
        container_combo.grid(row=row, column=0, padx=0, pady=5, sticky="ew")
        ctk.CTkLabel(
            scroll_frame,
            text="MKV - универсальный, MP4 - лучшая совместимость",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).grid(row=row+1, column=0, sticky="w", pady=(0, 20))
        row += 2
        
        # Кнопки
        btn_frame = ctk.CTkFrame(scroll_frame)
        btn_frame.grid(row=row, column=0, pady=20, sticky="e")
        
        def save_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Введите название пресета!", parent=dialog)
                return
            
            desc = desc_entry.get().strip()
            cq = int(cq_entry.get()) if cq_entry.get().isdigit() else 20
            codec = codec_var.get()
            scale = scale_var.get() if scale_var.get() else None
            remove_subs = remove_subs_var.get()
            stabilize = stabilize_var.get()
            container = container_var.get()

            new_preset = Preset(
                id=f"custom_{name.lower().replace(' ', '_')}",
                name=name,
                description=desc,
                video_codec=codec,
                cq=cq,
                scale=scale,
                remove_subtitles=remove_subs,
                stabilize=stabilize,
                container=container,
            )
            self.preset_manager.add_preset(new_preset)
            
            current = list(self.cmb_preset.cget("values"))
            current.append(name)
            self.cmb_preset.configure(values=current)
            self.cmb_preset.set(name)
            
            self.log_message(f"Пресет '{name}' сохранён!")
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="Отмена",
            command=lambda: dialog.destroy(),
            width=120
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Сохранить",
            command=save_preset,
            width=120,
            fg_color="green"
        ).pack(side="right", padx=5)

    def start_conversion(self):
        if not self.ffmpeg_available:
            result = messagebox.askyesno(
                "FFmpeg не найден",
                "FFmpeg не найден в системе!\n\nХотите установить его сейчас?",
                icon=messagebox.WARNING
            )
            if result:
                self._show_ffmpeg_warning()
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

        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()

    def run_conversion(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            output_folder = Path(self.selected_folder) / "output"
            output_folder.mkdir(exist_ok=True)

            for i, file in enumerate(self.files_list):
                self.lbl_progress.configure(text=f"Файл {i+1}/{len(self.files_list)}: {Path(file).name}")
                self.log_message(f"Начало: {Path(file).name}")

                output_ext = self.selected_preset.container
                output_file = str(output_folder / f"{Path(file).stem}-{self.selected_preset.video_codec}.{output_ext}")

                try:
                    preset_args = self.ffmpeg.get_preset_args(self.selected_preset.id)
                    success = loop.run_until_complete(
                        self.ffmpeg.convert(file, output_file, preset_args)
                    )

                    if success:
                        self.log_message(f"Успешно: {Path(output_file).name}")
                        self.lbl_status.configure(text="Готово!", text_color="green")
                    else:
                        self.log_message(f"Ошибка: {Path(file).name}")
                        self.lbl_status.configure(text="Ошибка конвертации", text_color="red")

                except Exception as ex:
                    self.log_message(f"Исключение: {str(ex)}")
                    self.lbl_status.configure(text=f"Ошибка: {str(ex)}", text_color="red")

                self.progress_bar.set(float(i + 1) / len(self.files_list))

            self.log_message("=== Конвертация завершена ===")

        finally:
            loop.close()
            self.is_converting = False
            self.btn_convert.configure(state="normal")
            self.btn_select_folder.configure(state="normal")
            self.cmb_preset.configure(state="normal")


if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()
