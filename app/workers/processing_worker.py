from PySide6.QtCore import (
    QThread,
    Signal,
)

from app.core.processor import (
    VideoProcessor,
    ProcessingError,
    ProcessingStopped,
)


class ProcessingWorker(QThread):

    progress = Signal(int)

    log = Signal(str)

    video_started = Signal(str)

    video_finished = Signal(str)

    error = Signal(str)

    finished = Signal()

    def __init__(
        self,
        videos,
        api_key,
        openai_model,
        whisper_model,
        source_language,
        target_language,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.videos = list(
            videos
        )

        self.api_key = api_key

        self.openai_model = (
            openai_model
        )

        self.whisper_model = (
            whisper_model
        )

        self.source_language = (
            source_language
        )

        self.target_language = (
            target_language
        )

        self._stop_requested = False

    # ========================================================
    # Stop
    # ========================================================

    def request_stop(self):

        self._stop_requested = True

        self.log.emit(
            "درخواست توقف پردازش دریافت شد..."
        )

    # ========================================================
    # Stop Checker
    # ========================================================

    def is_stop_requested(self):

        return self._stop_requested

    # ========================================================
    # Run
    # ========================================================

    def run(self):

        try:

            processor = VideoProcessor(
                api_key=self.api_key,
                openai_model=self.openai_model,
                whisper_model=self.whisper_model,
                source_language=self.source_language,
                target_language=self.target_language,
            )

            total = len(
                self.videos
            )

            if total == 0:

                self.log.emit(
                    "هیچ فایل ویدیویی برای پردازش وجود ندارد."
                )

                return

            self.log.emit(
                f"تعداد ویدیوها برای پردازش: {total}"
            )

            # ------------------------------------------------
            # Videos
            # ------------------------------------------------

            for index, video in enumerate(
                self.videos,
                start=1,
            ):

                if self._stop_requested:

                    break

                video_name = (
                    video.name
                )

                self.video_started.emit(
                    video_name
                )

                self.log.emit(
                    f"========== "
                    f"{index}/{total} "
                    f"=========="
                )

                self.log.emit(
                    f"▶ شروع: {video_name}"
                )

                try:

                    def video_progress(
                        value,
                        current_index=index,
                        current_total=total,
                    ):

                        overall_base = (
                            (
                                current_index
                                - 1
                            )
                            / current_total
                        ) * 100

                        overall_size = (
                            100
                            / current_total
                        )

                        overall_value = (
                            overall_base
                            + (
                                value
                                / 100
                            )
                            * overall_size
                        )

                        self.progress.emit(
                            int(
                                max(
                                    0,
                                    min(
                                        100,
                                        overall_value
                                    )
                                )
                            )
                        )

                    processor.process_video(
                        video_path=video,
                        progress_callback=(
                            video_progress
                        ),
                        log_callback=(
                            self.log.emit
                        ),
                        stop_checker=(
                            self.is_stop_requested
                        ),
                    )

                    if self._stop_requested:

                        break

                    self.video_finished.emit(
                        video_name
                    )

                    self.log.emit(
                        f"✓ پایان: {video_name}"
                    )

                except ProcessingStopped:

                    self.log.emit(
                        f"⏹ پردازش متوقف شد: "
                        f"{video_name}"
                    )

                    break

                except ProcessingError as exc:

                    self.error.emit(
                        f"{video_name}: {exc}"
                    )

                    self.log.emit(
                        f"✕ خطا: {video_name}"
                    )

                    # ادامه دادن به ویدیوی بعدی
                    continue

                except Exception as exc:

                    self.error.emit(
                        f"{video_name}: "
                        f"خطای غیرمنتظره: {exc}"
                    )

                    self.log.emit(
                        f"✕ خطای غیرمنتظره: "
                        f"{video_name}"
                    )

                    # ادامه دادن به ویدیوی بعدی
                    continue

            # ------------------------------------------------
            # Final State
            # ------------------------------------------------

            if self._stop_requested:

                self.log.emit(
                    "⏹ پردازش توسط کاربر متوقف شد."
                )

            else:

                self.progress.emit(
                    100
                )

                self.log.emit(
                    "✓ تمام فایل‌ها پردازش شدند."
                )

        except Exception as exc:

            self.error.emit(
                f"خطای اصلی Worker: {exc}"
            )

        finally:

            self.finished.emit()