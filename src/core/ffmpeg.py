import asyncio
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable


@dataclass
class VideoInfo:
    duration: float
    width: int
    height: int
    video_codec: str
    audio_codec: Optional[str]
    audio_channels: Optional[int]
    audio_bitrate: Optional[int]
    has_subtitles: bool


@dataclass
class ConversionProgress:
    file: str
    current: int
    total: int
    percentage: float
    speed: str
    eta: str


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

    async def get_video_info(self, file_path: str) -> VideoInfo:
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        data = json.loads(stdout.decode())

        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
        subtitle_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "subtitle"), {})

        return VideoInfo(
            duration=float(data.get("format", {}).get("duration", 0)),
            width=video_stream.get("width", 0),
            height=video_stream.get("height", 0),
            video_codec=video_stream.get("codec_name", ""),
            audio_codec=audio_stream.get("codec_name"),
            audio_channels=audio_stream.get("channels"),
            audio_bitrate=int(audio_stream.get("bit_rate", 0) // 1000) if audio_stream.get("bit_rate") else None,
            has_subtitles=bool(subtitle_stream)
        )

    async def convert(
        self,
        input_file: str,
        output_file: str,
        preset_args: list[str],
        callback: Optional[Callable] = None
    ) -> bool:
        cmd = [self.ffmpeg_path, "-y", "-i", input_file] + preset_args + [output_file]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        while True:
            if process.stderr is None:
                break
            line = await process.stderr.readline()
            if not line:
                break
            line_decoded = line.decode('utf-8', errors='ignore').strip()
            if callback and "time=" in line_decoded:
                time_str = line_decoded.split("time=")[1].split()[0]
                callback(time_str)

        await process.wait()
        return process.returncode == 0

    def get_preset_args(self, preset_name: str, custom_params: Optional[dict] = None) -> list[str]:
        presets = {
            # NVIDIA
            "h264_nvenc_standard": self._h264_nvenc_standard(custom_params),
            "h264_nvenc_light": self._h264_nvenc_light(custom_params),
            "h264_nvenc_mp4": self._h264_nvenc_mp4(custom_params),
            "hevc_nvenc_standard": self._hevc_nvenc_standard(custom_params),
            "hevc_nvenc_light": self._hevc_nvenc_light(custom_params),
            "hevc_nvenc_mp4": self._hevc_nvenc_mp4(custom_params),
            # Intel QuickSync
            "h264_qsv_standard": self._h264_qsv_standard(custom_params),
            "h264_qsv_light": self._h264_qsv_light(custom_params),
            "hevc_qsv_standard": self._hevc_qsv_standard(custom_params),
            "hevc_qsv_light": self._hevc_qsv_light(custom_params),
            # AMD AMF
            "h264_amf_standard": self._h264_amf_standard(custom_params),
            "h264_amf_light": self._h264_amf_light(custom_params),
            "hevc_amf_standard": self._hevc_amf_standard(custom_params),
            "hevc_amf_light": self._hevc_amf_light(custom_params),
        }
        return presets.get(preset_name, [])

    def _h264_nvenc_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _h264_nvenc_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _h264_nvenc_mp4(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "-0:s"
        ]

    def _hevc_nvenc_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "hevc_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_nvenc_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "hevc_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_nvenc_mp4(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "hevc_nvenc", "-rc", "vbr", "-cq", str(cq),
            "-g", "250", "-tune", "hq", "-rc-lookahead", "60",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "-0:s"
        ]

    def _h264_qsv_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "h264_qsv", "-q", str(cq),
            "-look_ahead", "1", "-b_ref_mode", "middle",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _h264_qsv_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "h264_qsv", "-q", str(cq),
            "-look_ahead", "1", "-b_ref_mode", "middle",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_qsv_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "hevc_qsv", "-q", str(cq),
            "-look_ahead", "1", "-b_ref_mode", "middle",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_qsv_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "hevc_qsv", "-q", str(cq),
            "-look_ahead", "1", "-b_ref_mode", "middle",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _h264_amf_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "h264_amf", "-quality", "quality", "-qp_i", str(cq), "-qp_p", str(cq),
            "-g", "250",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _h264_amf_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "h264_amf", "-quality", "speed", "-qp_i", str(cq), "-qp_p", str(cq),
            "-g", "250",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_amf_standard(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 20)
        return [
            "-map", "0:0", "-c:v", "hevc_amf", "-quality", "quality", "-qp_i", str(cq), "-qp_p", str(cq),
            "-g", "250",
            "-vf", "format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]

    def _hevc_amf_light(self, params: Optional[dict] = None) -> list[str]:
        p = params or {}
        cq = p.get("cq", 30)
        return [
            "-map", "0:0", "-c:v", "hevc_amf", "-quality", "speed", "-qp_i", str(cq), "-qp_p", str(cq),
            "-g", "250",
            "-vf", "scale=1920:-2,setsar=1:1,format=yuv420p",
            "-map", "0:a", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-map", "0:s:?", "-c:s", "srt"
        ]
