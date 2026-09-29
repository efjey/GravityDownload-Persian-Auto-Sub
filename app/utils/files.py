from pathlib import Path


def file_exists(path):
    return Path(path).exists()


def get_file_size(path):
    return Path(path).stat().st_size