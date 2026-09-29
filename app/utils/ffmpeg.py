import shutil
import subprocess
from pathlib import Path

from app.utils.config import FFMPEG_DIR


class FFmpegError(Exception):
    pass


class FFmpegManager:

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()

    # ========================================================
    # Find FFmpeg
    # ========================================================

    def _find_ffmpeg(self):

        candidates = []

        system_ffmpeg = shutil.which(
            "ffmpeg"
        )

        if system_ffmpeg:
            candidates.append(
                Path(system_ffmpeg)
            )

        candidates.extend(
            [
                FFMPEG_DIR / "ffmpeg.exe",
                FFMPEG_DIR / "bin" / "ffmpeg.exe",
            ]
        )

        for candidate in candidates:

            if candidate.exists():
                return str(candidate)

        return None

    # ========================================================
    # Availability
    # ========================================================

    def is_available(self):

        return bool(
            self.ffmpeg_path
        )

    # ========================================================
    # Version
    # ========================================================

    def get_version(self):

        if not self.ffmpeg_path:
            raise FFmpegError(
                "FFmpeg پیدا نشد."
            )

        try:

            result = subprocess.run(
                [
                    self.ffmpeg_path,
                    "-version",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )

            if result.returncode != 0:
                raise FFmpegError(
                    result.stderr.strip()
                )

            first_line = (
                result.stdout
                .splitlines()[0]
                if result.stdout
                else "Unknown"
            )

            return first_line

        except subprocess.TimeoutExpired:

            raise FFmpegError(
                "دریافت نسخه FFmpeg Timeout شد."
            )

        except Exception as exc:

            raise FFmpegError(
                f"خطا در اجرای FFmpeg:\n{exc}"
            )

    # ========================================================
    # Extract Audio
    # ========================================================

    def extract_audio(
        self,
        video_path,
        output_wav,
    ):

        if not self.ffmpeg_path:

            raise FFmpegError(
                "FFmpeg پیدا نشد.\n\n"
                "FFmpeg را در PATH ویندوز قرار دهید "
                "یا ffmpeg.exe را داخل پوشه ffmpeg پروژه قرار دهید."
            )

        video_path = Path(
            video_path
        )

        output_wav = Path(
            output_wav
        )

        output_wav.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        command = [
            self.ffmpeg_path,

            "-y",

            "-i",
            str(video_path),

            "-vn",

            "-ac",
            "1",

            "-ar",
            "16000",

            "-c:a",
            "pcm_s16le",

            str(output_wav),
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        except Exception as exc:

            raise FFmpegError(
                f"اجرای FFmpeg ناموفق بود:\n{exc}"
            )

        if result.returncode != 0:

            error_text = (
                result.stderr.strip()
                or "Unknown FFmpeg error."
            )

            raise FFmpegError(
                f"FFmpeg نتوانست صوت را استخراج کند:\n\n"
                f"{error_text[-3000:]}"
            )

        if not output_wav.exists():

            raise FFmpegError(
                "FFmpeg اجرا شد اما فایل WAV ایجاد نشد."
            )

        return output_wav