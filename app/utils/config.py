import os
from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# Project Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# Application
# ============================================================

APP_NAME = "GravityDownload Persian Auto Sub"
APP_VERSION = "0.3.0"


# ============================================================
# OpenAI
# ============================================================

# API Key دیگر از تنظیمات برنامه استفاده نمی‌شود.
# کاربر API Key خودش را مستقیماً داخل رابط کاربری وارد می‌کند.

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5-mini"
).strip()


# ============================================================
# Directories
# ============================================================

MODELS_DIR = PROJECT_ROOT / "models"

FFMPEG_DIR = PROJECT_ROOT / "ffmpeg"

TEMP_DIR = PROJECT_ROOT / "temp"

LOGS_DIR = PROJECT_ROOT / "logs"


# ============================================================
# Video Extensions
# ============================================================

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
    ".mpeg",
    ".mpg",
}


# ============================================================
# Supported Languages
# ============================================================

SUPPORTED_LANGUAGES = {
    "Auto Detect": None,

    "English": "en",
    "Persian": "fa",
    "Arabic": "ar",
    "Turkish": "tr",
    "Korean": "ko",
    "Japanese": "ja",
    "Chinese": "zh",
    "Chinese (Simplified)": "zh",
    "Chinese (Traditional)": "zh-TW",

    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Brazilian Portuguese": "pt-BR",

    "Russian": "ru",
    "Ukrainian": "uk",
    "Polish": "pl",
    "Dutch": "nl",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",

    "Czech": "cs",
    "Slovak": "sk",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Bulgarian": "bg",
    "Greek": "el",

    "Hebrew": "he",
    "Hindi": "hi",
    "Urdu": "ur",
    "Bengali": "bn",

    "Indonesian": "id",
    "Malay": "ms",
    "Vietnamese": "vi",
    "Thai": "th",

    "Filipino": "tl",

    "Persian (Dari)": "fa-AF",
    "Azerbaijani": "az",
    "Kazakh": "kk",
    "Uzbek": "uz",
    "Georgian": "ka",
    "Armenian": "hy",

    "Latin": "la",
}


# ============================================================
# Whisper Models
# ============================================================

WHISPER_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
]


# ============================================================
# Utility Functions
# ============================================================

def ensure_directories():
    """
    Create required application directories.
    """

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    FFMPEG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LOGS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def is_supported_video(file_path):
    """
    Check whether a file is a supported video.
    """

    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS