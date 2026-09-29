# GravityDownload Persian Auto Sub

A Windows desktop application for automatically generating Persian subtitles for video files.

The application scans a selected folder, extracts audio from videos, transcribes speech using Faster-Whisper, translates the transcription into Persian using OpenAI, and generates standard SRT subtitle files next to the original videos.

---

## Features

- Select a folder containing video files
- Automatic video file detection
- Audio extraction using FFmpeg
- Speech-to-text using Faster-Whisper
- NVIDIA GPU support through CUDA
- CPU fallback
- Automatic source-language detection
- Translation to Persian using OpenAI
- Batch translation
- Parallel translation requests
- Standard `.srt` subtitle generation
- Persian RTL subtitle support
- Progress tracking
- Processing logs
- Stop processing
- Skip existing subtitle files
- Windows desktop interface
- Dark UI built with PySide6

---

## Project Structure

```text
GravityDownload-Persian-Auto-Sub/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── processor.py
│   │   ├── transcriber.py
│   │   ├── translator.py
│   │   ├── subtitle.py
│   │   └── queue.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   └── widgets.py
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   └── processing_worker.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       ├── files.py
│       ├── ffmpeg.py
│       └── logger.py
│
├── ffmpeg/
│
├── models/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md