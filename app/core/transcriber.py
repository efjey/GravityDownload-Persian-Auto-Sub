import ctypes
import logging
import os
import sys
from pathlib import Path


logger = logging.getLogger("gravitydownload")


# ============================================================
# NVIDIA / CUDA DLL LOADER
# ============================================================

_DLL_HANDLES = []


def setup_nvidia_dlls():
    """
    Find all NVIDIA DLL directories inside the current venv,
    add them to PATH and Windows DLL search path, then
    preload important CUDA libraries.
    """

    python_exe = Path(sys.executable).resolve()

    # venv\Scripts\python.exe
    venv_root = python_exe.parent.parent

    site_packages = (
        venv_root
        / "Lib"
        / "site-packages"
    )

    nvidia_root = (
        site_packages
        / "nvidia"
    )

    if not nvidia_root.exists():

        logger.warning(
            f"NVIDIA package directory not found: "
            f"{nvidia_root}"
        )

        return

    # --------------------------------------------------------
    # Find every directory containing DLL files
    # --------------------------------------------------------

    dll_directories = set()

    for dll_file in nvidia_root.rglob("*.dll"):

        dll_directories.add(
            dll_file.parent
        )

    # --------------------------------------------------------
    # Add directories to PATH
    # --------------------------------------------------------

    current_path = os.environ.get(
        "PATH",
        ""
    )

    path_parts = current_path.split(
        os.pathsep
    )

    added_count = 0

    for directory in sorted(
        dll_directories,
        key=str
    ):

        directory_string = str(
            directory
        )

        if directory_string not in path_parts:

            path_parts.insert(
                0,
                directory_string
            )

            added_count += 1

        # Windows DLL search path
        if hasattr(
            os,
            "add_dll_directory"
        ):

            try:

                handle = (
                    os.add_dll_directory(
                        directory_string
                    )
                )

                _DLL_HANDLES.append(
                    handle
                )

            except Exception:
                pass

    os.environ["PATH"] = (
        os.pathsep.join(
            path_parts
        )
    )

    logger.info(
        f"NVIDIA DLL directory ها اضافه شدند: "
        f"{added_count}"
    )

    # --------------------------------------------------------
    # Find and preload cuBLAS
    # --------------------------------------------------------

    cublas_files = list(
        nvidia_root.rglob(
            "cublas64_12.dll"
        )
    )

    if not cublas_files:

        logger.warning(
            "cublas64_12.dll پیدا نشد."
        )

    else:

        cublas_path = cublas_files[0]

        logger.info(
            f"cuBLAS پیدا شد: "
            f"{cublas_path}"
        )

        try:

            ctypes.WinDLL(
                str(cublas_path)
            )

            logger.info(
                "cublas64_12.dll با موفقیت preload شد."
            )

        except Exception as exc:

            logger.warning(
                "preload کردن cuBLAS ناموفق بود: "
                f"{exc}"
            )

    # --------------------------------------------------------
    # Find and preload cuDNN
    # --------------------------------------------------------

    cudnn_files = list(
        nvidia_root.rglob(
            "cudnn*.dll"
        )
    )

    if cudnn_files:

        for cudnn_path in cudnn_files:

            try:

                ctypes.WinDLL(
                    str(cudnn_path)
                )

            except Exception:
                pass

        logger.info(
            f"cuDNN DLL ها بررسی شدند: "
            f"{len(cudnn_files)}"
        )


# IMPORTANT:
# Must happen before importing faster-whisper.
setup_nvidia_dlls()


# ============================================================
# Faster Whisper
# ============================================================

try:

    from faster_whisper import WhisperModel

except Exception as exc:

    raise ImportError(
        "Faster-Whisper قابل بارگذاری نیست:\n"
        f"{exc}"
    ) from exc


# ============================================================
# Exception
# ============================================================

class TranscriptionError(Exception):
    pass


# ============================================================
# Transcriber
# ============================================================

class Transcriber:

    def __init__(
        self,
        model_size="small",
        device="auto",
        compute_type="auto",
    ):

        self.model_size = (
            model_size or "small"
        )

        self.requested_device = (
            device or "auto"
        )

        self.requested_compute_type = (
            compute_type or "auto"
        )

        self.device = None
        self.compute_type = None
        self.model = None
        self.using_gpu = False

    # ========================================================
    # Load
    # ========================================================

    def load_model(self):

        if self.model is not None:
            return

        logger.info(
            f"در حال آماده‌سازی Whisper مدل "
            f"{self.model_size}..."
        )

        if self.requested_device == "cpu":

            self._load_cpu()
            return

        # ----------------------------------------------------
        # Try GPU
        # ----------------------------------------------------

        try:

            self._load_gpu()
            return

        except Exception as exc:

            logger.error(
                "بارگذاری Whisper روی GPU ناموفق بود:"
            )

            logger.error(
                str(exc)
            )

            if (
                self.requested_device
                == "cuda"
            ):

                raise TranscriptionError(
                    self._format_gpu_error(
                        exc
                    )
                ) from exc

            logger.warning(
                "در حال استفاده از CPU..."
            )

        # ----------------------------------------------------
        # CPU fallback
        # ----------------------------------------------------

        self._load_cpu()

    # ========================================================
    # GPU
    # ========================================================

    def _load_gpu(self):

        logger.info(
            "در حال بررسی CUDA..."
        )

        try:

            import ctranslate2

        except Exception as exc:

            raise RuntimeError(
                f"CTranslate2 قابل بارگذاری نیست: {exc}"
            )

        try:

            supported_types = (
                ctranslate2.get_supported_compute_types(
                    "cuda"
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "CUDA توسط CTranslate2 قابل استفاده نیست:\n"
                f"{exc}"
            )

        logger.info(
            f"CUDA Compute Types: "
            f"{supported_types}"
        )

        # ----------------------------------------------------
        # Select compute type
        # ----------------------------------------------------

        requested = (
            self.requested_compute_type
        )

        if (
            requested
            and requested != "auto"
        ):

            compute_type = requested

        elif "float16" in supported_types:

            compute_type = "float16"

        elif (
            "int8_float16"
            in supported_types
        ):

            compute_type = "int8_float16"

        else:

            raise RuntimeError(
                "هیچ Compute Type مناسب برای CUDA پیدا نشد."
            )

        logger.info(
            f"CUDA فعال شد. "
            f"Compute type: {compute_type}"
        )

        logger.info(
            "در حال بارگذاری مدل Whisper روی GPU..."
        )

        try:

            model = WhisperModel(
                self.model_size,
                device="cuda",
                compute_type=compute_type,
            )

        except Exception as exc:

            raise RuntimeError(
                f"Whisper GPU initialization failed:\n"
                f"{exc}"
            ) from exc

        self.model = model

        self.device = "cuda"

        self.compute_type = (
            compute_type
        )

        self.using_gpu = True

        logger.info(
            f"Whisper با موفقیت روی GPU "
            f"بارگذاری شد: {self.model_size}"
        )

    # ========================================================
    # CPU
    # ========================================================

    def _load_cpu(self):

        logger.info(
            "در حال بارگذاری Whisper روی CPU..."
        )

        try:

            model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )

        except Exception as exc:

            raise TranscriptionError(
                "بارگذاری Whisper روی CPU نیز "
                "ناموفق بود:\n"
                f"{exc}"
            ) from exc

        self.model = model

        self.device = "cpu"

        self.compute_type = "int8"

        self.using_gpu = False

        logger.info(
            f"Whisper روی CPU آماده شد: "
            f"{self.model_size}"
        )

    # ========================================================
    # Transcribe
    # ========================================================

    def transcribe(
        self,
        audio_path,
        language=None,
    ):

        audio_path = Path(
            audio_path
        )

        if not audio_path.exists():

            raise TranscriptionError(
                f"فایل صوتی پیدا نشد:\n"
                f"{audio_path}"
            )

        try:

            self.load_model()

            logger.info(
                "شروع تشخیص گفتار "
                f"(device={self.device}, "
                f"compute={self.compute_type})"
            )

            language_code = (
                language
                if language
                else None
            )

            if language_code:

                logger.info(
                    f"زبان Whisper: "
                    f"{language_code}"
                )

            else:

                logger.info(
                    "زبان Whisper: Auto Detect"
                )

            try:

                segments, info = (
                    self.model.transcribe(
                        str(audio_path),
                        language=language_code,
                        # Speed-oriented settings for subtitle generation.
                        # A smaller beam is substantially faster while
                        # retaining good subtitle accuracy.
                        beam_size=3,
                        vad_filter=True,
                        condition_on_previous_text=False,
                        word_timestamps=False,
                    )
                )

                result = []

                index = 1

                for segment in segments:

                    text = (
                        segment.text
                        or ""
                    ).strip()

                    if not text:
                        continue

                    start = float(
                        segment.start
                    )

                    end = float(
                        segment.end
                    )

                    if end <= start:
                        continue

                    result.append(
                        {
                            "index": index,
                            "start": start,
                            "end": end,
                            "text": text,
                        }
                    )

                    index += 1

                detected_language = getattr(
                    info,
                    "language",
                    None
                )

                language_probability = getattr(
                    info,
                    "language_probability",
                    None
                )

                logger.info(
                    f"زبان شناسایی‌شده: "
                    f"{detected_language or 'unknown'}"
                )

                if (
                    language_probability
                    is not None
                ):

                    logger.info(
                        f"اطمینان تشخیص زبان: "
                        f"{language_probability:.2%}"
                    )

                logger.info(
                    f"تعداد سگمنت‌ها: "
                    f"{len(result)}"
                )

                if not result:

                    raise TranscriptionError(
                        "Whisper هیچ گفتاری "
                        "در فایل پیدا نکرد."
                    )

                return {
                    "segments": result,
                    "language": detected_language,
                    "language_probability": (
                        language_probability
                    ),
                    "device": self.device,
                    "compute_type": (
                        self.compute_type
                    ),
                    "using_gpu": (
                        self.using_gpu
                    ),
                }

            except Exception as exc:

                # ------------------------------------------------
                # GPU runtime failure
                # ------------------------------------------------

                error_text = str(
                    exc
                )

                if (
                    self.using_gpu
                    and (
                        "cublas64_12.dll"
                        in error_text.lower()
                        or
                        "cudnn"
                        in error_text.lower()
                    )
                ):

                    logger.error(
                        "CUDA هنگام اجرای واقعی Whisper "
                        "خطا داد."
                    )

                    logger.error(
                        error_text
                    )

                    raise TranscriptionError(
                        self._format_gpu_error(
                            exc
                        )
                    ) from exc

                raise

        except TranscriptionError:

            raise

        except Exception as exc:

            raise TranscriptionError(
                "خطا در تبدیل گفتار به متن:\n"
                f"{exc}"
            ) from exc

    # ========================================================
    # Error
    # ========================================================

    @staticmethod
    def _format_gpu_error(
        exc
    ):

        message = str(
            exc
        )

        if (
            "cublas64_12.dll"
            in message.lower()
        ):

            return (
                "کتابخانه cublas64_12.dll "
                "هنگام اجرای Whisper قابل بارگذاری نیست.\n\n"
                "مسیر DLLهای NVIDIA در برنامه ثبت شده "
                "اما یکی از وابستگی‌های native آن قابل "
                "بارگذاری نیست.\n\n"
                f"جزئیات:\n{message}"
            )

        if "cudnn" in message.lower():

            return (
                "کتابخانه cuDNN هنگام اجرای "
                "Whisper قابل بارگذاری نیست.\n\n"
                f"جزئیات:\n{message}"
            )

        return (
            "اجرای Whisper روی GPU ناموفق بود.\n\n"
            f"جزئیات:\n{message}"
        )