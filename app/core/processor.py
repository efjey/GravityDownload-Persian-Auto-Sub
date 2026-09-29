from pathlib import Path
from typing import Callable, Optional

from app.core.transcriber import (
    Transcriber,
    TranscriptionError,
)

from app.core.translator import (
    Translator,
    TranslationError,
)

from app.core.subtitle import (
    write_srt,
)

from app.utils.ffmpeg import (
    FFmpegManager,
    FFmpegError,
)

from app.utils.config import (
    SUPPORTED_LANGUAGES,
)


class ProcessingError(Exception):
    """
    خطای عمومی پردازش ویدیو.
    """
    pass


class ProcessingStopped(Exception):
    """
    پردازش توسط کاربر متوقف شده است.
    """
    pass


class VideoProcessor:

    def __init__(
        self,
        api_key: str,
        openai_model: str = "gpt-5-mini",
        whisper_model: str = "small",
        source_language: Optional[str] = None,
        target_language: str = "fa",
        batch_size: int = 60,
        max_workers: int = 3,
    ):

        self.api_key = api_key

        self.openai_model = (
            openai_model
            or "gpt-5-mini"
        )

        self.whisper_model = (
            whisper_model
            or "small"
        )

        self.source_language = (
            source_language
        )

        self.target_language = (
            target_language
            or "fa"
        )

        self.batch_size = max(
            1,
            int(batch_size)
        )

        self.max_workers = max(
            1,
            int(max_workers)
        )

        # ----------------------------------------------------
        # FFmpeg
        # ----------------------------------------------------

        self.ffmpeg = FFmpegManager()

        # ----------------------------------------------------
        # Whisper
        # ----------------------------------------------------

        self.transcriber = Transcriber(
            model_size=self.whisper_model
        )

        # ----------------------------------------------------
        # Translator
        # ----------------------------------------------------

        self.translator = Translator(
            api_key=self.api_key,
            model=self.openai_model,
        )

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _emit_log(
        callback,
        message: str,
    ):

        if callback is not None:

            try:
                callback(
                    str(message)
                )

            except Exception:
                pass

    @staticmethod
    def _emit_progress(
        callback,
        value: int,
    ):

        if callback is None:
            return

        value = max(
            0,
            min(
                100,
                int(value)
            )
        )

        try:
            callback(value)

        except Exception:
            pass

    @staticmethod
    def _check_stop(
        stop_checker
    ):

        if stop_checker is None:
            return

        try:

            if stop_checker():

                raise ProcessingStopped(
                    "پردازش توسط کاربر متوقف شد."
                )

        except ProcessingStopped:

            raise

        except Exception:
            pass

    # ========================================================
    # Language
    # ========================================================

    @staticmethod
    def _normalize_source_language(
        language
    ):

        if not language:
            return None

        language = str(
            language
        ).strip()

        if not language:
            return None

        # اگر قبلاً کد زبان است
        if len(language) <= 5:
            return language.lower()

        # اگر نام زبان از UI آمده باشد
        code = SUPPORTED_LANGUAGES.get(
            language
        )

        if code:
            return code

        return language

    @staticmethod
    def _normalize_target_language(
        language
    ):

        if not language:
            return "fa"

        language = str(
            language
        ).strip()

        # اگر کد زبان است
        if len(language) <= 5:

            return language.lower()

        # اگر نام زبان از UI آمده باشد
        code = SUPPORTED_LANGUAGES.get(
            language
        )

        if code:
            return code

        return language

    # ========================================================
    # Progress
    # ========================================================

    @staticmethod
    def _stage_progress(
        stage_start,
        stage_end,
        stage_value,
    ):

        stage_value = max(
            0,
            min(
                100,
                stage_value
            )
        )

        return int(
            stage_start
            + (
                stage_value
                / 100
            )
            * (
                stage_end
                - stage_start
            )
        )

    # ========================================================
    # Process Video
    # ========================================================

    def process_video(
        self,
        video_path,
        progress_callback=None,
        log_callback=None,
        stop_checker=None,
    ):

        video_path = Path(
            video_path
        )

        if not video_path.exists():

            raise ProcessingError(
                f"فایل ویدیو پیدا نشد: {video_path}"
            )

        if not video_path.is_file():

            raise ProcessingError(
                f"مسیر واردشده فایل نیست: {video_path}"
            )

        subtitle_path = (
            video_path.with_suffix(
                ".srt"
            )
        )

        audio_path = (
            video_path.with_name(
                f".{video_path.stem}_gravitydownload_audio.wav"
            )
        )

        try:

            # ------------------------------------------------
            # Start
            # ------------------------------------------------

            self._check_stop(
                stop_checker
            )

            self._emit_progress(
                progress_callback,
                0
            )

            self._emit_log(
                log_callback,
                f"شروع پردازش: {video_path.name}"
            )

            self._emit_log(
                log_callback,
                f"Whisper: {self.whisper_model}"
            )

            self._emit_log(
                log_callback,
                f"OpenAI: {self.openai_model}"
            )

            # ------------------------------------------------
            # Existing SRT
            # ------------------------------------------------

            if subtitle_path.exists():

                self._emit_log(
                    log_callback,
                    f"⚠ زیرنویس از قبل وجود دارد: "
                    f"{subtitle_path.name}"
                )

                self._emit_log(
                    log_callback,
                    "برای جلوگیری از بازنویسی، "
                    "این فایل رد شد."
                )

                self._emit_progress(
                    progress_callback,
                    100
                )

                return subtitle_path

            # ------------------------------------------------
            # FFmpeg
            # ------------------------------------------------

            self._check_stop(
                stop_checker
            )

            self._emit_log(
                log_callback,
                "🎵 استخراج صدا با FFmpeg..."
            )

            self._emit_progress(
                progress_callback,
                5
            )

            try:

                self.ffmpeg.extract_audio(
                    video_path,
                    audio_path,
                )

            except FFmpegError as exc:

                raise ProcessingError(
                    f"خطا در استخراج صدا: {exc}"
                ) from exc

            self._emit_progress(
                progress_callback,
                25
            )

            self._emit_log(
                log_callback,
                "✓ استخراج صدا انجام شد."
            )

            # ------------------------------------------------
            # Whisper
            # ------------------------------------------------

            self._check_stop(
                stop_checker
            )

            source_language = (
                self._normalize_source_language(
                    self.source_language
                )
            )

            if source_language:

                self._emit_log(
                    log_callback,
                    f"🎙️ تشخیص گفتار "
                    f"(زبان: {source_language})..."
                )

            else:

                self._emit_log(
                    log_callback,
                    "🎙️ تشخیص گفتار "
                    "(تشخیص خودکار زبان)..."
                )

            self._emit_progress(
                progress_callback,
                30
            )

            try:

                transcription = (
                    self.transcriber.transcribe(
                        audio_path,
                        language=source_language,
                    )
                )

            except TranscriptionError as exc:

                raise ProcessingError(
                    f"خطا در Whisper: {exc}"
                ) from exc

            except Exception as exc:

                raise ProcessingError(
                    f"خطای تشخیص گفتار: {exc}"
                ) from exc

            self._check_stop(
                stop_checker
            )

            if not isinstance(
                transcription,
                dict
            ):

                raise ProcessingError(
                    "خروجی Whisper ساختار معتبری ندارد."
                )

            segments = (
                transcription.get(
                    "segments",
                    []
                )
            )

            detected_language = (
                transcription.get(
                    "language"
                )
            )

            language_probability = (
                transcription.get(
                    "language_probability"
                )
            )

            using_gpu = (
                transcription.get(
                    "using_gpu"
                )
            )

            if not segments:

                raise ProcessingError(
                    "Whisper هیچ گفتاری در ویدیو پیدا نکرد."
                )

            self._emit_progress(
                progress_callback,
                50
            )

            self._emit_log(
                log_callback,
                f"✓ Whisper: "
                f"{len(segments)} بخش گفتاری پیدا شد."
            )

            if detected_language:

                if language_probability is not None:

                    self._emit_log(
                        log_callback,
                        "زبان تشخیص‌داده‌شده: "
                        f"{detected_language} "
                        f"("
                        f"{language_probability:.1%}"
                        f")"
                    )

                else:

                    self._emit_log(
                        log_callback,
                        f"زبان تشخیص‌داده‌شده: "
                        f"{detected_language}"
                    )

            if using_gpu:

                self._emit_log(
                    log_callback,
                    "⚡ Whisper با GPU اجرا شد."
                )

            else:

                self._emit_log(
                    log_callback,
                    "Whisper با CPU اجرا شد."
                )

            # ------------------------------------------------
            # Translation
            # ------------------------------------------------

            self._check_stop(
                stop_checker
            )

            target_language = (
                self._normalize_target_language(
                    self.target_language
                )
            )

            self._emit_log(
                log_callback,
                f"🌐 ترجمه {len(segments)} بخش "
                f"به {target_language}..."
            )

            self._emit_progress(
                progress_callback,
                55
            )

            def translation_progress(
                value
            ):

                self._check_stop(
                    stop_checker
                )

                overall = (
                    self._stage_progress(
                        55,
                        92,
                        value
                    )
                )

                self._emit_progress(
                    progress_callback,
                    overall
                )

            def translation_stop_checker():

                if stop_checker is None:
                    return False

                try:
                    return bool(
                        stop_checker()
                    )

                except Exception:
                    return False

            try:

                translated_segments = (
                    self.translator.translate_batch(
                        segments=segments,
                        batch_size=self.batch_size,
                        max_workers=self.max_workers,
                        progress_callback=(
                            translation_progress
                        ),
                        stop_callback=(
                            translation_stop_checker
                        ),
                    )
                )

            except TranslationError as exc:

                raise ProcessingError(
                    f"خطا در ترجمه: {exc}"
                ) from exc

            except Exception as exc:

                raise ProcessingError(
                    f"خطای ترجمه: {exc}"
                ) from exc

            self._check_stop(
                stop_checker
            )

            if not translated_segments:

                raise ProcessingError(
                    "ترجمه‌ای دریافت نشد."
                )

            if len(translated_segments) != len(
                segments
            ):

                raise ProcessingError(
                    "تعداد بخش‌های ترجمه‌شده "
                    "با بخش‌های اصلی برابر نیست."
                )

            self._emit_progress(
                progress_callback,
                92
            )

            self._emit_log(
                log_callback,
                "✓ ترجمه تمام شد."
            )

            # ------------------------------------------------
            # SRT
            # ------------------------------------------------

            self._check_stop(
                stop_checker
            )

            self._emit_log(
                log_callback,
                "📝 ساخت فایل SRT..."
            )

            self._emit_progress(
                progress_callback,
                95
            )

            try:

                write_srt(
                    translated_segments,
                    subtitle_path,
                )

            except Exception as exc:

                raise ProcessingError(
                    f"خطا در ساخت SRT: {exc}"
                ) from exc

            self._check_stop(
                stop_checker
            )

            self._emit_progress(
                progress_callback,
                100
            )

            self._emit_log(
                log_callback,
                f"✓ زیرنویس ساخته شد: "
                f"{subtitle_path.name}"
            )

            return subtitle_path

        except ProcessingStopped:

            self._emit_log(
                log_callback,
                "⏹ پردازش این ویدیو متوقف شد."
            )

            raise

        except ProcessingError:

            raise

        except Exception as exc:

            raise ProcessingError(
                f"خطای پردازش ویدیو: {exc}"
            ) from exc

        finally:

            # ------------------------------------------------
            # Temporary audio cleanup
            # ------------------------------------------------

            try:

                if audio_path.exists():

                    audio_path.unlink()

                    self._emit_log(
                        log_callback,
                        "فایل موقت صوتی حذف شد."
                    )

            except Exception as exc:

                self._emit_log(
                    log_callback,
                    f"⚠ حذف فایل موقت ناموفق بود: {exc}"
                )