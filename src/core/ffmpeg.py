import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .presets import Preset


class FFmpegWrapper:
    def __init__(self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()

    def _find_ffmpeg(self) -> str:
        local_ffmpeg = Path(__file__).parent.parent.parent / "ffmpeg"
        if local_ffmpeg.exists():
            if platform.system() == "Windows":
                exe = local_ffmpeg / "ffmpeg.exe"
                if exe.exists():
                    return str(exe)
            else:
                exe = local_ffmpeg / "ffmpeg"
                if exe.exists():
                    return str(exe)
        return "ffmpeg"

    def _find_ffprobe(self) -> str:
        local_ffprobe = Path(__file__).parent.parent.parent / "ffmpeg"
        if local_ffprobe.exists():
            if platform.system() == "Windows":
                exe = local_ffprobe / "ffprobe.exe"
                if exe.exists():
                    return str(exe)
            else:
                exe = local_ffprobe / "ffprobe"
                if exe.exists():
                    return str(exe)
        return "ffprobe"

    def convert(self, input_file: str, output_file: str, 
            preset: Preset | None = None, worker_thread=None) -> bool:
        """Конвертация с использованием Preset объекта
        
        Args:
            worker_thread: ссылка на WorkerThread для доступа к process
        """
        if preset:
            preset_args = self._generate_preset_args(preset)
        else:
            return False
        
        cmd = [self.ffmpeg_path, "-y", "-i", input_file, "-nostats", "-loglevel", "error"] + preset_args + [output_file]
        process = None
        
        try:
            if sys.platform == "win32":
                CREATE_NO_WINDOW = 0x08000000
                process = subprocess.Popen(
                    cmd,
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            
            if worker_thread:
                worker_thread.process = process
                
            process.wait()
            return process.returncode == 0
        except KeyboardInterrupt:
            try:
                if process:
                    process.kill()
                    process.wait()
            except (ProcessLookupError, OSError):
                pass
            return False
        except Exception:
            return False
    
    def _generate_preset_args(self, preset: Preset) -> list[str]:
        """Генерация аргументов FFmpeg на основе пресета"""
        args = []
        
        if preset.hw_accelerator == "nvenc":
            args.extend(["-c:v", f"{preset.codec_type}_nvenc"])
            args.extend(["-preset", "p3", "-rc", "vbr", "-cq", str(preset.cq)])
            args.extend(["-g", "250", "-tune", "hq", "-rc-lookahead", "60"])
        elif preset.hw_accelerator == "qsv":
            args.extend(["-c:v", f"{preset.codec_type}_qsv"])
            args.extend(["-preset", "fast", "-q", str(preset.cq)])
        elif preset.hw_accelerator == "amf":
            args.extend(["-c:v", f"{preset.codec_type}_amf"])
            quality = "quality" if preset.cq <= 20 else ("balanced" if preset.cq <= 30 else "speed")
            args.extend(["-quality", quality, "-qp_i", str(preset.cq), "-qp_p", str(preset.cq)])
            args.append("-g")
            args.append("250")
        else:
            if preset.codec_type == "hevc":
                args.extend(["-c:v", "libx265", "-preset", "medium", "-crf", str(preset.cq)])
            else:
                args.extend(["-c:v", "libx264", "-preset", "medium", "-crf", str(preset.cq)])
        
        if preset.scale:
            args.extend(["-vf", f"scale={preset.scale},setsar=1:1,format=yuv420p"])
        else:
            args.extend(["-vf", "format=yuv420p"])
        
        if preset.remove_subtitles:
            args.append("-sn")
        
        channels = preset.audio_channels
        if channels == 6:
            args.extend(["-c:a", "aac", "-ac", "6", "-b:a", "448k"])
        elif channels == 8:
            args.extend(["-c:a", "aac", "-ac", "8", "-b:a", "512k"])
        else:
            args.extend(["-c:a", "aac", "-ac", "2", "-b:a", preset.audio_bitrate])
        
        if preset.container == "mp4":
            args.extend(["-movflags", "+faststart"])
        
        return args
