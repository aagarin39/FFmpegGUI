import ctypes
import datetime
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

# DPI awareness для Windows
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# Импорт для работы в скомпилированном приложении
if getattr(sys, "frozen", False):
    import src.core.ffmpeg
    import src.core.ffmpeg_installer
    import src.core.ffmpeg_updater
    import src.core.presets

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
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.ffmpeg_installer import FFmpegInstaller
        from core.ffmpeg_updater import FFmpegUpdater
        from core.presets import PresetManager, Preset


class ConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка окна - фиксированный размер для стабильности
        self.title("FFmpeg Converter")
        self.geometry("1100x750")
        self.resizable(True, True)
        self.minsize(850, 600)

        # Отключаем перерисовку во время движения окна
        self._moving = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Состояние
        self.ffmpeg_available = False
        self.ffmpeg_version = ""
        self.is_installing = False

        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()

        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None

        self._create_ui()
        self.after(300, self._init_ffmpeg)

    def _init_ffmpeg(self):
        self._check_ffmpeg()
        self.after(8000, self._check_updates)

    def _check_ffmpeg(self):
        self.ffmpeg_available = shutil.which("ffmpeg") is not None
        install_dir = Path.home() / "FFmpegGUI" / "ffmpeg"
        if (install_dir / "ffmpeg.exe").exists():
            self.ffmpeg_available = True

        if self.ffmpeg_available:
            self.ffmpeg_version = FFmpegInstaller.get_ffmpeg_version()
            self.status_lbl.configure(
                text=f"✓ FFmpeg {self.ffmpeg_version}",
                text_color="#22c55e",
            )
            self.status_lbl.bind("<Button-1>", lambda e: self._ffmpeg_menu())
            self.status_lbl.configure(cursor="hand2")
            self.install_banner.pack_forget()
        else:
            self.status_lbl.configure(text="✗ FFmpeg не найден", text_color="#ef4444")
            self.install_banner.pack(fill="x", padx=20, pady=5)

    def _check_updates(self):
        try:
            if FFmpegUpdater.should_notify():
                self.update_banner.pack(fill="x", padx=20, pady=5, before=self.main_frame)
        except Exception:
            pass

    def _create_ui(self):
        # ===== Header =====
        header = ctk.CTkFrame(self, height=50, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="FFmpeg Converter",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            header,
            text="Проверка...",
            font=ctk.CTkFont(size=12),
            text_color="#6b7280",
        )
        self.status_lbl.pack(side="right")

        # ===== Баннер установки =====
        self.install_banner = ctk.CTkFrame(self, fg_color="#d97706", height=50)
        self.install_banner.pack(fill="x", padx=20, pady=5)
        self.install_banner.pack_propagate(False)
        self.install_banner.pack_forget()  # Скрыт по умолчанию

        ctk.CTkLabel(
            self.install_banner,
            text="⚠️  FFmpeg не найден. Установите для работы.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkButton(
            self.install_banner,
            text="Установить",
            command=self._install_ffmpeg,
            width=130,
            height=32,
            fg_color="#15803d",
        ).pack(side="right", padx=20, pady=8)

        # ===== Баннер обновления =====
        self.update_banner = ctk.CTkFrame(self, fg_color="#0284c7", height=50)
        self.update_banner.pack(fill="x", padx=20, pady=5)
        self.update_banner.pack_propagate(False)
        self.update_banner.pack_forget()

        ctk.CTkLabel(
            self.update_banner,
            text="🔄 Доступна новая версия FFmpeg",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkButton(
            self.update_banner,
            text="Обновить",
            command=self._install_ffmpeg,
            width=90,
            height=30,
            fg_color="#15803d",
        ).pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            self.update_banner,
            text="✕",
            command=lambda: self.update_banner.pack_forget(),
            width=30,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color="white",
        ).pack(side="right", padx=5, pady=10)

        # ===== Основной контент =====
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Панель выбора папки
        folder_frame = ctk.CTkFrame(self.main_frame)
        folder_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            folder_frame,
            text="📁 Выбрать папку",
            command=self._select_folder,
            width=150,
        ).pack(side="left", padx=10, pady=10)

        self.folder_lbl = ctk.CTkLabel(
            folder_frame,
            text="Папка не выбрана",
            text_color="#6b7280",
        )
        self.folder_lbl.pack(side="left", padx=15, pady=10)

        # Пресеты
        preset_frame = ctk.CTkFrame(self.main_frame)
        preset_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            preset_frame,
            text="Пресет:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=(10, 10), pady=10)

        self.preset_var = ctk.StringVar()
        presets = [p.name for p in self.preset_manager.get_all_presets()]
        self.preset_combo = ctk.CTkComboBox(
            preset_frame,
            values=presets,
            variable=self.preset_var,
            command=self._preset_changed,
            width=320,
        )
        self.preset_combo.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            preset_frame,
            text="🛠 Конструктор",
            command=self._preset_builder,
            width=140,
        ).pack(side="left", padx=15, pady=10)

        self.preset_info = ctk.CTkLabel(
            preset_frame,
            text="",
            text_color="#6b7280",
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        self.preset_info.pack(side="left", padx=15, pady=10)

        # Список файлов
        files_container = ctk.CTkFrame(self.main_frame)
        files_container.pack(fill="both", expand=True, pady=(0, 10))

        self.files_frame = ctk.CTkScrollableFrame(files_container)
        self.files_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.files_count = ctk.CTkLabel(
            files_container,
            text="Файлов: 0",
            text_color="#6b7280",
        )
        self.files_count.pack(anchor="w", padx=5, pady=5)

        # Прогресс
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill="x", pady=(0, 10))

        self.convert_btn = ctk.CTkButton(
            progress_frame,
            text="▶ Конвертировать",
            command=self._convert,
            width=170,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.convert_btn.pack(side="left", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_lbl = ctk.CTkLabel(
            progress_frame,
            text="",
            text_color="#6b7280",
            width=200,
        )
        self.progress_lbl.pack(side="right", padx=10, pady=5)

        # Статус конвертации
        self.convert_status = ctk.CTkLabel(
            self.main_frame,
            text="",
            text_color="#22c55e",
            font=ctk.CTkFont(size=11),
        )
        self.convert_status.pack(anchor="w", padx=5, pady=(0, 10))

        # Лог
        log_frame = ctk.CTkFrame(self.main_frame)
        log_frame.pack(fill="x")

        ctk.CTkLabel(
            log_frame,
            text="Лог:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        self.log_txt = ctk.CTkTextbox(log_frame, height=60, state="disabled")
        self.log_txt.pack(fill="x", padx=5, pady=5)

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Папка с файлами")
        if folder:
            self.selected_folder = folder
            self.folder_lbl.configure(text=folder)
            self.files_list = []

            for w in self.files_frame.winfo_children():
                w.destroy()

            exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

            for f in Path(folder).iterdir():
                if f.is_file() and f.suffix.lower() in exts:
                    self.files_list.append(str(f))
                    row = ctk.CTkFrame(self.files_frame)
                    row.pack(fill="x", pady=1, padx=5)
                    ctk.CTkLabel(row, text=f.name, anchor="w").pack(side="left", padx=10, pady=4)
                    ctk.CTkLabel(row, text=f"{f.stat().st_size // 1024} KB", text_color="#6b7280").pack(side="right", padx=10, pady=4)

            self.files_count.configure(text=f"Файлов: {len(self.files_list)}")

    def _preset_changed(self, value):
        if value:
            p = self.preset_manager.get_preset_by_name(value)
            if p:
                self.selected_preset = p
                self.preset_info.configure(text=p.description)

    def _install_ffmpeg(self):
        if self.is_installing:
            return
        self.is_installing = True
        self.update_banner.pack_forget()

        def on_progress(s, pct):
            pass  # Не обновляем кнопку во время движения

        def done(ok):
            self.is_installing = False
            self._check_ffmpeg()
            if ok:
                self._log(f"✓ FFmpeg установлен: {FFmpegInstaller.get_ffmpeg_version()}")

        threading.Thread(target=lambda: done(FFmpegInstaller.install(on_progress)), daemon=True).start()

    def _ffmpeg_menu(self):
        if not self.ffmpeg_available:
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("FFmpeg")
        dlg.geometry("400x400")
        dlg.resizable(False, False)
        dlg.transient(self)

        f = ctk.CTkFrame(dlg)
        f.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            f,
            text=f"✓ FFmpeg {self.ffmpeg_version}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#22c55e",
        ).pack(pady=15)

        ctk.CTkLabel(
            f,
            text=f"Путь: {FFmpegInstaller.INSTALL_DIR}",
            text_color="#9ca3af",
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=10)

        ctk.CTkButton(
            f,
            text="📁 Открыть папку",
            command=lambda: subprocess.run(["explorer", str(FFmpegInstaller.INSTALL_DIR)]),
            width=180,
        ).pack(pady=8)

        ctk.CTkButton(
            f,
            text="🗑️ Удалить",
            command=lambda: self._uninstall(dlg),
            width=180,
            fg_color="#dc2626",
        ).pack(pady=8)

        ctk.CTkButton(
            f,
            text="Закрыть",
            command=dlg.destroy,
            width=180,
            fg_color="transparent",
            border_width=2,
        ).pack(pady=15)

    def _uninstall(self, dlg):
        if FFmpegInstaller.uninstall():
            dlg.destroy()
            self._check_ffmpeg()
            self._log("✓ FFmpeg удалён")

    def _preset_builder(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Конструктор пресетов")
        dlg.geometry("480x620")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        f = ctk.CTkFrame(dlg)
        f.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            f,
            text="Новый пресет",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(0, 15))

        def add_row(parent, label, widget):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, width=120).pack(side="left")
            widget.pack(side="left", fill="x", expand=True)
            return row

        name = ctk.CTkEntry(f, placeholder_text="Название", width=300)
        add_row(f, "Название:", name)

        desc = ctk.CTkEntry(f, placeholder_text="Описание", width=300)
        add_row(f, "Описание:", desc)

        hw = ctk.CTkComboBox(f, values=["nvenc", "qsv", "amf", "cpu"], width=300)
        hw.set("nvenc")
        add_row(f, "Ускорение:", hw)

        codec = ctk.CTkComboBox(f, values=["h264", "hevc"], width=300)
        codec.set("h264")
        add_row(f, "Кодек:", codec)

        cq = ctk.CTkEntry(f, placeholder_text="20", width=300)
        add_row(f, "CQ (1-51):", cq)

        scale = ctk.CTkComboBox(f, values=["", "1920:-2", "1280:-2", "3840:-2"], width=300)
        scale.set("")
        add_row(f, "Масштаб:", scale)

        audio = ctk.CTkComboBox(f, values=["2", "6", "8"], width=300)
        audio.set("2")
        add_row(f, "Аудио каналы:", audio)

        container = ctk.CTkComboBox(f, values=["mkv", "mp4"], width=300)
        container.set("mkv")
        add_row(f, "Контейнер:", container)

        subs = ctk.CTkCheckBox(f, text="Удалить субтитры")
        subs.pack(anchor="w", pady=10)

        def save():
            n = name.get().strip()
            if not n:
                return

            h = hw.get() if hw.get() != "cpu" else None
            p = Preset(
                id=f"custom_{n.lower().replace(' ', '_')}",
                name=n,
                description=desc.get().strip(),
                hw_accelerator=h,
                codec_type=codec.get(),
                cq=int(cq.get()) if cq.get().isdigit() else 20,
                scale=scale.get() if scale.get() else None,
                audio_channels=int(audio.get()),
                remove_subtitles=subs.get(),
                container=container.get(),
            )
            self.preset_manager.add_preset(p)
            self.preset_combo.configure(values=[x.name for x in self.preset_manager.get_all_presets()])
            self._log(f"✓ Пресет: {n}")
            dlg.destroy()

        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(pady=15)

        ctk.CTkButton(btns, text="Сохранить", command=save, width=130, fg_color="#15803d").pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Отмена", command=dlg.destroy, width=130, fg_color="transparent", border_width=2).pack(side="left", padx=10)

    def _convert(self):
        if not self.ffmpeg_available:
            self.convert_status.configure(text="✗ FFmpeg не найден", text_color="#ef4444")
            return
        if not self.files_list:
            self.convert_status.configure(text="⚠️ Нет файлов", text_color="#f59e0b")
            return
        if not self.selected_preset:
            self.convert_status.configure(text="⚠️ Нет пресета", text_color="#f59e0b")
            return

        self.convert_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.convert_status.configure(text="Конвертация...", text_color="#f59e0b")

        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self):
        out = Path(self.selected_folder) / "output"
        out.mkdir(exist_ok=True)

        ok = 0
        err = 0

        for i, file in enumerate(self.files_list):
            name = Path(file).name
            self._log(f"▶ {name}")

            ext = self.selected_preset.container if self.selected_preset.container else "mkv"
            output = str(out / f"{Path(file).stem}.{ext}")

            try:
                if self.ffmpeg.convert(file, output, self.selected_preset):
                    ok += 1
                    self._log(f"✓ {name}")
                else:
                    err += 1
                    self._log(f"✗ {name}")
            except Exception as e:
                err += 1
                self._log(f"✗ {name}: {e}")

            pct = (i + 1) / len(self.files_list)
            self.after(0, lambda p=pct, n=name: self._progress(p, n))

        self.after(0, lambda: self._done(ok, err))

    def _progress(self, val, name):
        self.progress_bar.set(val)
        self.progress_lbl.configure(text=name)

    def _done(self, ok, err):
        self.convert_btn.configure(state="normal")
        total = ok + err
        if err == 0:
            self.convert_status.configure(text=f"✓ Готово: {ok}/{total}", text_color="#22c55e")
        else:
            self.convert_status.configure(text=f"⚠️ {ok} успешно, {err} ошибок", text_color="#f59e0b")
        self._log(f"=== {ok} успешно, {err} ошибок ===")

    def _log(self, msg):
        if hasattr(self, "log_txt"):
            self.log_txt.configure(state="normal")
            t = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_txt.insert("end", f"[{t}] {msg}\n")
            self.log_txt.see("end")
            self.log_txt.configure(state="disabled")


def main():
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
