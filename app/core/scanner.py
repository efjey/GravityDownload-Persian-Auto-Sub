from pathlib import Path


class VideoScanner:
    """
    Finds supported video files inside a directory.
    """

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
    }

    def scan(self, folder: Path):
        if not folder.exists():
            return []

        if not folder.is_dir():
            return []

        videos = []

        for path in folder.iterdir():
            if not path.is_file():
                continue

            if path.suffix.lower() in self.VIDEO_EXTENSIONS:
                videos.append(path)

        return sorted(
            videos,
            key=lambda item: item.name.lower()
        )