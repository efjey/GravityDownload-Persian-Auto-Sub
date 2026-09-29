from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import copy
from typing import Callable, Optional

from openai import OpenAI


logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """خطای مربوط به ترجمه."""


class TranslationStopped(Exception):
    """ترجمه توسط کاربر متوقف شده است."""


class Translator:
    """
    مترجم فارسی مبتنی بر OpenAI Responses API.

    امکانات:
    - تست اتصال API
    - ترجمه Batchای
    - چند درخواست همزمان
    - Retry خودکار
    - حفظ ترتیب Segmentها
    - امکان توقف
    """

    DEFAULT_BATCH_SIZE = 60
    DEFAULT_MAX_WORKERS = 3

    MAX_RETRIES = 3
    RETRY_DELAYS = (2, 5, 10)

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-mini",
    ):
        self.api_key = (api_key or "").strip()
        self.model = model

        self._stop_event = threading.Event()

        if not self.api_key:
            raise TranslationError(
                "OpenAI API key is empty."
            )

        try:
            self.client = OpenAI(
                api_key=self.api_key
            )
        except Exception as exc:
            raise TranslationError(
                f"Could not initialize OpenAI client: {exc}"
            ) from exc

    # =========================================================
    # STOP CONTROL
    # =========================================================

    def request_stop(self):
        """درخواست توقف ترجمه."""
        self._stop_event.set()

    def reset_stop(self):
        """پاک کردن وضعیت توقف."""
        self._stop_event.clear()

    def is_stop_requested(self) -> bool:
        """بررسی وضعیت توقف."""
        return self._stop_event.is_set()

    def _check_stop(self):
        if self.is_stop_requested():
            raise TranslationStopped(
                "Translation stopped by user."
            )

    # =========================================================
    # API CONNECTION TEST
    # =========================================================

    def test_connection(self) -> bool:
        """
        تست اتصال API.

        این متد برای دکمه «تست API» در رابط کاربری استفاده می‌شود.

        در صورت موفقیت:
            True

        در صورت خطا:
            TranslationError
        """

        if not self.api_key:
            raise TranslationError(
                "OpenAI API key is empty."
            )

        try:
            logger.info(
                "Testing OpenAI API connection..."
            )

            # یک درخواست بسیار کوچک برای تست واقعی API.
            response = self.client.responses.create(
                model=self.model,
                input=(
                    "Reply with exactly one word: OK"
                ),
                max_output_tokens=16,
            )

            output = getattr(
                response,
                "output_text",
                "",
            )

            if output is None:
                output = ""

            output = str(output).strip()

            logger.info(
                "OpenAI API connection successful."
            )

            if output:
                logger.debug(
                    "API test response: %s",
                    output,
                )

            return True

        except Exception as exc:
            logger.error(
                "OpenAI API connection test failed: %s",
                exc,
            )

            raise TranslationError(
                f"OpenAI API connection failed: {exc}"
            ) from exc

    # =========================================================
    # BATCH TRANSLATION
    # =========================================================

    def translate_batch(
        self,
        segments,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        progress_callback: Optional[
            Callable[[int, int, int], None]
        ] = None,
        stop_callback: Optional[
            Callable[[], bool]
        ] = None,
    ):
        """
        ترجمه Segmentها به صورت Batch.

        progress_callback:
            completed_batches,
            total_batches,
            translated_segments

        stop_callback:
            تابعی که اگر True برگرداند، پردازش متوقف می‌شود.
        """

        if not segments:
            return []

        if not self.api_key:
            raise TranslationError(
                "OpenAI API key is empty."
            )

        self.reset_stop()

        batch_size = max(
            1,
            int(batch_size),
        )

        max_workers = max(
            1,
            int(max_workers),
        )

        batches = []

        for start in range(
            0,
            len(segments),
            batch_size,
        ):
            end = min(
                start + batch_size,
                len(segments),
            )

            batches.append(
                segments[start:end]
            )

        total_batches = len(batches)

        logger.info(
            "Starting translation: "
            "%d segments / %d batches / %d workers",
            len(segments),
            total_batches,
            max_workers,
        )

        results = [
            None
            for _ in range(total_batches)
        ]

        completed_batches = 0
        translated_segments = 0

        # -----------------------------------------------------
        # CALLBACK
        # -----------------------------------------------------

        def report_progress():
            if progress_callback is None:
                return

            try:
                progress_callback(
                    completed_batches,
                    total_batches,
                    translated_segments,
                )
            except Exception:
                logger.exception(
                    "Translation progress callback failed."
                )

        # -----------------------------------------------------
        # STOP CHECK
        # -----------------------------------------------------

        def check_external_stop():
            if self.is_stop_requested():
                return True

            if stop_callback is not None:
                try:
                    if stop_callback():
                        self.request_stop()
                        return True
                except Exception:
                    logger.exception(
                        "Stop callback failed."
                    )

            return False

        # -----------------------------------------------------
        # WORKER
        # -----------------------------------------------------

        def translate_single_batch(
            batch_index: int,
            batch,
        ):
            if check_external_stop():
                raise TranslationStopped(
                    "Translation stopped by user."
                )

            logger.info(
                "Translating batch %d/%d (%d segments)",
                batch_index + 1,
                total_batches,
                len(batch),
            )

            translated = self._translate_with_retry(
                batch
            )

            return (
                batch_index,
                translated,
            )

        # -----------------------------------------------------
        # EXECUTOR
        # -----------------------------------------------------

        executor = ThreadPoolExecutor(
            max_workers=max_workers
        )

        futures = []

        try:
            for index, batch in enumerate(batches):

                if check_external_stop():
                    raise TranslationStopped(
                        "Translation stopped by user."
                    )

                future = executor.submit(
                    translate_single_batch,
                    index,
                    batch,
                )

                futures.append(future)

            for future in as_completed(futures):

                if check_external_stop():
                    raise TranslationStopped(
                        "Translation stopped by user."
                    )

                batch_index, translated = (
                    future.result()
                )

                results[batch_index] = translated

                completed_batches += 1
                translated_segments += len(
                    translated
                )

                logger.info(
                    "Batch completed: %d/%d",
                    completed_batches,
                    total_batches,
                )

                report_progress()

        except TranslationStopped:
            self.request_stop()

            for future in futures:
                future.cancel()

            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

            raise

        except Exception:
            for future in futures:
                future.cancel()

            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

            raise

        else:
            executor.shutdown(
                wait=True
            )

        # -----------------------------------------------------
        # FLATTEN IN ORIGINAL ORDER
        # -----------------------------------------------------

        final_segments = []

        for batch_result in results:

            if batch_result is None:
                raise TranslationError(
                    "A translation batch returned no result."
                )

            final_segments.extend(
                batch_result
            )

        if len(final_segments) != len(segments):
            raise TranslationError(
                "Translated segment count does not "
                "match the original segment count."
            )

        logger.info(
            "Translation completed successfully: %d segments",
            len(final_segments),
        )

        return final_segments

    # =========================================================
    # SINGLE BATCH + RETRY
    # =========================================================

    def _translate_with_retry(
        self,
        batch,
    ):

        last_error = None

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:
                self._check_stop()

                return self._translate_one_batch(
                    batch
                )

            except TranslationStopped:
                raise

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "Translation attempt %d/%d failed: %s",
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )

                if attempt >= self.MAX_RETRIES:
                    break

                delay_index = min(
                    attempt - 1,
                    len(self.RETRY_DELAYS) - 1,
                )

                delay = self.RETRY_DELAYS[
                    delay_index
                ]

                logger.info(
                    "Retrying in %d seconds...",
                    delay,
                )

                for _ in range(delay):
                    self._check_stop()
                    time.sleep(1)

        raise TranslationError(
            f"Translation failed after "
            f"{self.MAX_RETRIES} attempts: "
            f"{last_error}"
        ) from last_error

    # =========================================================
    # OPENAI REQUEST
    # =========================================================

    def _translate_one_batch(
        self,
        batch,
    ):
        """
        ارسال یک Batch به OpenAI.
        """

        if not batch:
            return []

        numbered_lines = []

        for index, segment in enumerate(
            batch,
            start=1,
        ):

            text = self._get_segment_text(
                segment
            )

            numbered_lines.append(
                f"[{index}] {text}"
            )

        source_text = "\n".join(
            numbered_lines
        )

        prompt = f"""
You are a professional subtitle translator.

Translate the following subtitle segments into natural, fluent Persian.

IMPORTANT RULES:

1. Translate every segment.
2. Keep exactly the same number of segments.
3. Keep the original numbering exactly.
4. Do NOT merge segments.
5. Do NOT split segments.
6. Do NOT remove segments.
7. Preserve names, brands, software names, technical terms,
   model numbers and other terms that should remain in English.
8. English words must stay in the correct semantic position
   inside the Persian sentence.
9. Do not move English words to the beginning or end just
   because Persian is written right-to-left.
10. Preserve numbers correctly.
11. Preserve technical notation such as:
    RTX 4060, Windows 11, Python 3, USB-C, 1080p, 4K, etc.
12. Do not add explanations.
13. Do not add comments.
14. Output ONLY the translated numbered segments.

Example:

Input:
[1] I installed Windows 11 yesterday.
[2] The RTX 4060 is very fast.

Output:
[1] من دیروز Windows 11 را نصب کردم.
[2] کارت RTX 4060 خیلی سریع است.

Now translate:

{source_text}
""".strip()

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )

        except Exception as exc:
            raise TranslationError(
                f"OpenAI request failed: {exc}"
            ) from exc

        output = getattr(
            response,
            "output_text",
            None,
        )

        if output is None:
            raise TranslationError(
                "OpenAI returned an empty response."
            )

        output = str(output).strip()

        if not output:
            raise TranslationError(
                "OpenAI returned an empty translation."
            )

        translated_texts = (
            self._parse_translation_response(
                output,
                expected_count=len(batch),
            )
        )

        if len(translated_texts) != len(batch):
            raise TranslationError(
                "Translation result count mismatch. "
                f"Expected {len(batch)}, "
                f"received {len(translated_texts)}."
            )

        translated_segments = []

        for segment, translated_text in zip(
            batch,
            translated_texts,
        ):

            translated_segments.append(
                self._replace_segment_text(
                    segment,
                    translated_text,
                )
            )

        return translated_segments

    # =========================================================
    # RESPONSE PARSER
    # =========================================================

    def _parse_translation_response(
        self,
        response_text: str,
        expected_count: int,
    ):
        """
        تبدیل پاسخ:

        [1] متن
        [2] متن

        به لیست متن‌ها.
        """

        lines = response_text.splitlines()

        results = {}

        current_index = None
        current_parts = []

        for raw_line in lines:

            line = raw_line.strip()

            if not line:
                continue

            parsed_index = None
            parsed_text = None

            # ---------------------------------------------
            # Find [number]
            # ---------------------------------------------

            if line.startswith("["):

                close_bracket = line.find("]")

                if close_bracket > 1:

                    number_text = line[
                        1:close_bracket
                    ].strip()

                    if number_text.isdigit():

                        parsed_index = int(
                            number_text
                        )

                        parsed_text = line[
                            close_bracket + 1:
                        ].strip()

            # ---------------------------------------------
            # New numbered segment
            # ---------------------------------------------

            if parsed_index is not None:

                if current_index is not None:
                    results[current_index] = (
                        " ".join(
                            current_parts
                        ).strip()
                    )

                current_index = parsed_index

                current_parts = []

                if parsed_text:
                    current_parts.append(
                        parsed_text
                    )

            else:

                if current_index is not None:
                    current_parts.append(
                        line
                    )

        # Last segment
        if current_index is not None:
            results[current_index] = (
                " ".join(
                    current_parts
                ).strip()
            )

        # ---------------------------------------------
        # Validate numbering
        # ---------------------------------------------

        translated = []

        for index in range(
            1,
            expected_count + 1,
        ):

            if index not in results:
                raise TranslationError(
                    f"Missing translated segment [{index}]."
                )

            text = results[index].strip()

            if not text:
                raise TranslationError(
                    f"Translated segment [{index}] is empty."
                )

            translated.append(text)

        return translated

    # =========================================================
    # SEGMENT HELPERS
    # =========================================================

    @staticmethod
    def _get_segment_text(
        segment,
    ) -> str:

        if isinstance(segment, dict):
            return str(
                segment.get("text", "")
            )

        return str(
            getattr(
                segment,
                "text",
                "",
            )
        )

    @staticmethod
    def _replace_segment_text(
        segment,
        translated_text: str,
    ):
        """
        جایگزینی فقط متن Segment
        و حفظ timestampها.
        """

        if isinstance(segment, dict):

            new_segment = dict(segment)

            new_segment["text"] = (
                translated_text
            )

            return new_segment

        try:
            new_segment = copy(segment)

            setattr(
                new_segment,
                "text",
                translated_text,
            )

            return new_segment

        except Exception as exc:
            raise TranslationError(
                f"Could not replace segment text: {exc}"
            ) from exc